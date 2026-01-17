
"""
Orchestrator and multi-modal router
"""

import os
import json
import logging
from typing import List, Dict, Optional
from backboard import BackboardClient
from dotenv import load_dotenv
from app.services.master_builder import MasterBuilder, VoxelCluster

load_dotenv()

logger = logging.getLogger(__name__)

class BackboardService:
    def __init__(self):
        # Initializing the 'Single API' for 2200+ models
        self.client = BackboardClient(api_key=os.getenv("BACKBOARD_API_KEY"))
        self.assistant_id = None
        
        # Initialize the Master Builder (Source of Truth for 3D grid)
        self.master_builder = MasterBuilder()
        
        # Scene Deltas: History of all changes for interactive instructions
        # Each delta represents a change to the Three.js scene
        self.scene_deltas: List[Dict] = []
        
        # Thread ID to scene deltas mapping (for multi-session support)
        self.thread_deltas: Dict[str, List[Dict]] = {}
        
        # Define the tools the AI can use to interact with your LEGO logic
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "place_brick",
                    "description": "Registers a LEGO brick into the 3D grid and master inventory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "part_id": {"type": "string", "description": "Official LEGO part ID"},
                            "color_id": {"type": "integer", "description": "Rebrickable color ID"},
                            "position": {"type": "array", "items": {"type": "integer"}, "description": "[x, y, z]"},
                            "is_ai_filled": {"type": "boolean", "description": "Set to true if this brick fills a visual gap"}
                        },
                        "required": ["part_id", "color_id", "position"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "finalize_assembly_step",
                    "description": "Groups placed bricks into a logical instruction step.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "integer"},
                            "description": {"type": "string"}
                        }
                    }
                }
            }
        ]

    async def get_or_create_lego_assistant(self):
        """Sets up the Master Builder with 'Auto' memory and pre-defined tools."""
        if self.assistant_id:
            return self.assistant_id

        assistant = await self.client.create_assistant(
            name="LEGO Master Builder",
            description="Expert in structural engineering and 3D LEGO synthesis. Uses Twelve Labs data to build worlds.",
            memory="Auto", 
            metadata={"project": "lego-playground"}
        )
        self.assistant_id = assistant.assistant_id
        return self.assistant_id

    async def start_session(self, scenery_data: dict):
        """
        Starts a stateful thread and anchors it with Scenery JSON.
        This initializes the Master Builder with the scenery as ground truth.
        """
        assistant_id = await self.get_or_create_lego_assistant()
        thread = await self.client.create_thread(assistant_id=assistant_id)

        # Initialize Master Builder with scenery anchor
        self.master_builder.initialize_scenery(scenery_data)

        # Inject Scenery as the persistent 'Ground Truth' in thread memory
        await self.client.add_message(
            thread_id=thread.thread_id,
            role="system",
            content=f"SCENERY ANCHOR LOADED: {json.dumps(scenery_data)}. Every object added hereafter must align with this coordinate system. If objects overlap or have missing data, use your 'place_brick' tool to fill gaps logically."
        )
        return thread.thread_id

    async def add_object_to_world(self, thread_id: str, object_data: dict, use_high_thinking: bool = True):
        """
        Processes an individual object and handles gap-filling via Tool Calls.
        
        Args:
            thread_id: Thread ID for the session
            object_data: Object data from TwelveLabs analysis
            use_high_thinking: If True, use Gemini 3 Pro (Architectural Phase),
                              If False, use Gemini 3 Flash (Bulk Phase)
        """
        # Phase 1: Architectural Phase (High Thinking) - Gap filling and structural design
        if use_high_thinking:
            prompt = (
                f"ARCHITECTURAL PHASE: Integrate this object into the playground: {json.dumps(object_data)}. "
                "Analyze the memory of the scenery and the new object to decide where to fill gaps or place support beams. "
                "1. Check for stability against the scenery. "
                "2. Identify missing surfaces or structural gaps. "
                "3. Generate 'ai_filled' bricks to complete the shape or add supports. "
                "4. Use the 'place_brick' tool strategically for structural integrity."
            )

            # Record model switch delta
            model_delta = self._create_scene_delta(
                timestamp=len(self.scene_deltas),
                action="model_switch",
                model_switch="gemini-3-pro"
            )
            self._add_scene_delta(thread_id, model_delta)
            
            # Use Gemini 3 Pro for high-reasoning gap filling
            response = await self.client.add_message(
                thread_id=thread_id,
                content=prompt,
                model_name="gemini-3-pro",  # High Thinking for architectural decisions
                tools=self.tools,
                stream=False
            )

            # Handle the Tool Execution Loop
            if response.status == "REQUIRES_ACTION":
                await self._handle_tool_calls(thread_id, response.tool_calls)
        
        # Phase 2: Bulk Phase (Low Thinking) - Fill solid areas rapidly
        # Record model switch to Flash
        model_delta = self._create_scene_delta(
            timestamp=len(self.scene_deltas),
            action="model_switch",
            model_switch="gemini-3-flash"
        )
        self._add_scene_delta(thread_id, model_delta)
        
        bulk_prompt = (
            f"BULK PHASE: Fill the remaining solid areas of this object: {json.dumps(object_data)}. "
            "Use greedy volume fitting: place the largest possible bricks first (2x4, then 2x3, etc.) "
            "to minimize part count. Use the 'place_brick' tool for all remaining placements."
        )
        
        bulk_response = await self.client.add_message(
            thread_id=thread_id,
            content=bulk_prompt,
            model_name="gemini-3-flash",  # Low Thinking for rapid bulk filling
            tools=self.tools,
            stream=False
        )
        
        if bulk_response.status == "REQUIRES_ACTION":
            await self._handle_tool_calls(thread_id, bulk_response.tool_calls)
        
        # Phase 3: Apply engineering rules after placement
        self._apply_engineering_rules(object_data)
        
        # Get final state
        grid_state = self.master_builder.get_grid_state()
        return {
            "status": "completed",
            "grid_state": grid_state,
            "content": bulk_response.content if hasattr(bulk_response, 'content') else "Object integrated"
        }

    async def _handle_tool_calls(self, thread_id, tool_calls):
        """
        Executes the Python logic for the AI's requested brick placements.
        This is where the Master Builder's register_brick is called.
        Also records Scene Deltas for interactive instructions.
        """
        results = []
        timestamp = len(self.scene_deltas)  # Sequential timestamp
        
        for call in tool_calls:
            if call.function.name == "place_brick":
                args = json.loads(call.function.arguments)
                
                # Call Master Builder to register the brick
                success = self.master_builder.register_brick(
                    part_id=args.get("part_id"),
                    color_id=args.get("color_id"),
                    position=tuple(args.get("position", [0, 0, 0])),
                    dimensions=tuple(args.get("dimensions", [1, 1, 1])) if "dimensions" in args else None,
                    is_ai_filled=args.get("is_ai_filled", False)
                )
                
                logger.info(f"🧱 AI placing brick: {args['part_id']} at {args['position']} - Success: {success}")
                
                if success:
                    # Record Scene Delta for this brick placement
                    scene_delta = self._create_scene_delta(
                        timestamp=timestamp,
                        action="add_brick",
                        brick_id=f"brick_{args['part_id']}_{timestamp}",
                        part_id=args.get("part_id"),
                        color_id=args.get("color_id"),
                        position=list(args.get("position", [0, 0, 0])),
                        dimensions=list(args.get("dimensions", [1, 1, 1])) if "dimensions" in args else [1, 1, 1],
                        is_ai_filled=args.get("is_ai_filled", False),
                        model_switch=None  # Will be set if model changes
                    )
                    self._add_scene_delta(thread_id, scene_delta)
                    timestamp += 1
                
                results.append({
                    "tool_call_id": call.id,
                    "output": json.dumps({"status": "success" if success else "failed", "placed": success})
                })
            elif call.function.name == "finalize_assembly_step":
                args = json.loads(call.function.arguments)
                logger.info(f"📋 Finalizing assembly step {args.get('step_number')}: {args.get('description')}")
                
                # Record step delta
                step_delta = self._create_scene_delta(
                    timestamp=timestamp,
                    action="step_marker",
                    step_number=args.get("step_number"),
                    description=args.get("description")
                )
                self._add_scene_delta(thread_id, step_delta)
                timestamp += 1
                
                results.append({
                    "tool_call_id": call.id,
                    "output": json.dumps({"status": "step_finalized"})
                })

        # Submit results back to Backboard to finalize the turn
        final_turn = await self.client.submit_tool_outputs(
            thread_id=thread_id,
            tool_outputs=results
        )
        return final_turn.content if hasattr(final_turn, 'content') else None
    
    def _apply_engineering_rules(self, object_data: dict):
        """
        Apply the three core engineering rules after object placement:
        1. Laminar Interlocking check
        2. Connectivity Audit (for floating parts)
        Note: Greedy Volume Fitting is applied during placement
        """
        # Rule 2: Check laminar interlocking for all layers
        max_layer = max(self.master_builder.layer_bricks.keys()) if self.master_builder.layer_bricks else 0
        for layer in range(max_layer + 1):
            interlock_bricks = self.master_builder.check_laminar_interlocking(layer)
            if interlock_bricks:
                logger.info(f"🔗 Applied laminar interlocking: added {len(interlock_bricks)} bricks to layer {layer + 1}")
        
        # Rule 3: Connectivity Audit - check for floating parts
        disconnected_clusters = self.master_builder.connectivity_audit()
        if disconnected_clusters:
            logger.warning(f"⚠️  Found {len(disconnected_clusters)} disconnected clusters")
            # In a real implementation, this would trigger Gemini 3 Pro to "hallucinate" structural supports
            # For now, we log the clusters that need attention
            for i, cluster in enumerate(disconnected_clusters):
                logger.warning(f"  Cluster {i+1}: {len(cluster.voxels)} floating voxels at bbox {cluster.bounding_box}")
    
    def get_master_builder_state(self) -> dict:
        """Get the current state of the Master Builder"""
        return self.master_builder.get_grid_state()
    
    def _create_scene_delta(
        self,
        timestamp: int,
        action: str,
        brick_id: Optional[str] = None,
        part_id: Optional[str] = None,
        color_id: Optional[int] = None,
        position: Optional[List[int]] = None,
        dimensions: Optional[List[int]] = None,
        is_ai_filled: Optional[bool] = None,
        model_switch: Optional[str] = None,
        step_number: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict:
        """
        Create a Scene Delta representing a change to the Three.js scene.
        
        Scene Deltas tell the frontend which objects to show/hide for timeline scrubbing.
        """
        delta = {
            "timestamp": timestamp,
            "action": action,
            "threejs_object_id": brick_id,  # ID of the Three.js object to show/hide
        }
        
        if action == "add_brick":
            delta.update({
                "visible": True,  # Show this brick
                "part_id": part_id,
                "color_id": color_id,
                "position": position,
                "dimensions": dimensions,
                "is_ai_filled": is_ai_filled,
                "model_switch": model_switch  # e.g., "gemini-3-pro" -> "gemini-3-flash"
            })
        elif action == "step_marker":
            delta.update({
                "step_number": step_number,
                "description": description
            })
        elif action == "model_switch":
            delta.update({
                "from_model": model_switch,
                "to_model": model_switch
            })
        
        return delta
    
    def _add_scene_delta(self, thread_id: str, delta: Dict):
        """Add a scene delta to the history for a thread"""
        if thread_id not in self.thread_deltas:
            self.thread_deltas[thread_id] = []
        self.thread_deltas[thread_id].append(delta)
        self.scene_deltas.append(delta)
    
    def get_interactive_instructions(self, thread_id: str) -> List[Dict]:
        """
        Get interactive instructions as a list of Scene Deltas.
        
        Each delta tells the frontend which Three.js objects to show/hide
        for timeline scrubbing. The frontend can step through these deltas
        to visualize the "History of Creation".
        
        Returns:
            List of Scene Deltas, each representing a change to the scene
        """
        if thread_id not in self.thread_deltas:
            return []
        
        deltas = self.thread_deltas[thread_id]
        
        # Add model switch markers if needed
        enhanced_deltas = []
        current_model = None
        
        for delta in deltas:
            # Track model switches
            if delta.get("model_switch"):
                if current_model and current_model != delta["model_switch"]:
                    enhanced_deltas.append({
                        "timestamp": delta["timestamp"],
                        "action": "model_switch",
                        "from_model": current_model,
                        "to_model": delta["model_switch"],
                        "description": f"Switched from {current_model} to {delta['model_switch']}"
                    })
                current_model = delta["model_switch"]
            
            enhanced_deltas.append(delta)
        
        return enhanced_deltas
    
    def get_instruction_timeline(self, thread_id: str) -> Dict:
        """
        Get a complete timeline of instructions with metadata.
        
        Returns:
            Dictionary with timeline metadata and deltas
        """
        deltas = self.get_interactive_instructions(thread_id)
        
        # Count different action types
        action_counts = {}
        for delta in deltas:
            action = delta.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            "thread_id": thread_id,
            "total_deltas": len(deltas),
            "action_counts": action_counts,
            "deltas": deltas,
            "metadata": {
                "description": "History of Creation - Every brick choice, model switch, and structural fix",
                "format": "threejs_scene_deltas",
                "version": "1.0"
            }
        }