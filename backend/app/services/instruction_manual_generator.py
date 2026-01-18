"""
Instruction Manual Generator
Creates step-by-step building instructions from LEGO manifests.
Organizes bricks by layer and provides guided assembly workflow.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BuildStep:
    """Represents a single step in the build process"""
    step_number: int
    layer_z: int
    bricks_in_step: List[Dict]  # Bricks to place in this step
    piece_counts: Dict[str, int]  # Part ID -> quantity for this step
    instructions: str  # Human-readable instructions


@dataclass
class BuildGuide:
    """Complete building guide for a project"""
    project_name: str
    total_steps: int
    total_bricks: int
    estimated_time_minutes: int
    difficulty: str  # "Easy", "Medium", "Hard"
    steps: List[BuildStep]
    layer_summary: Dict[int, str]  # Layer number -> description


class InstructionManualGenerator:
    """
    Generates step-by-step building instructions from manifests.
    """
    
    # Time estimation: average seconds per brick placement
    TIME_PER_BRICK = 3  # seconds
    
    @staticmethod
    def generate_build_guide(manifest: Dict, project_name: str = "LEGO Build") -> BuildGuide:
        """
        Generate step-by-step building guide from manifest.
        
        Args:
            manifest: The build manifest with bricks and layer data
            project_name: Name of the project
            
        Returns:
            BuildGuide with organized steps
        """
        try:
            # Group bricks by layer
            bricks_by_layer = defaultdict(list)
            total_bricks = 0
            
            for brick in manifest.get("bricks", []):
                z = brick.get("position", [0, 0, 0])[2]
                bricks_by_layer[z].append(brick)
                total_bricks += 1
            
            # Sort layers
            sorted_layers = sorted(bricks_by_layer.keys())
            
            # Generate steps (one per layer, or group small layers)
            steps = []
            step_number = 1
            
            for layer_idx, z in enumerate(sorted_layers):
                bricks_in_layer = bricks_by_layer[z]
                
                # Count pieces for this layer
                piece_counts = defaultdict(int)
                for brick in bricks_in_layer:
                    part_id = brick.get("part_id")
                    piece_counts[part_id] += 1
                
                # Generate step instructions
                instructions = InstructionManualGenerator._generate_step_instructions(
                    step_number=step_number,
                    layer_z=z,
                    layer_num=layer_idx + 1,
                    bricks=bricks_in_layer,
                    piece_counts=dict(piece_counts)
                )
                
                step = BuildStep(
                    step_number=step_number,
                    layer_z=z,
                    bricks_in_step=bricks_in_layer,
                    piece_counts=dict(piece_counts),
                    instructions=instructions
                )
                
                steps.append(step)
                step_number += 1
            
            # Estimate difficulty
            if total_bricks < 50:
                difficulty = "Easy"
            elif total_bricks < 150:
                difficulty = "Medium"
            else:
                difficulty = "Hard"
            
            # Estimate time (in minutes)
            estimated_time = max(5, (total_bricks * InstructionManualGenerator.TIME_PER_BRICK) // 60)
            
            # Generate layer summary
            layer_summary = {}
            for z, bricks in bricks_by_layer.items():
                layer_summary[z] = f"Layer {z}: {len(bricks)} bricks placed"
            
            return BuildGuide(
                project_name=project_name,
                total_steps=len(steps),
                total_bricks=total_bricks,
                estimated_time_minutes=estimated_time,
                difficulty=difficulty,
                steps=steps,
                layer_summary=layer_summary
            )
        
        except Exception as e:
            logger.error(f"Error generating build guide: {e}")
            return BuildGuide(
                project_name=project_name,
                total_steps=0,
                total_bricks=0,
                estimated_time_minutes=0,
                difficulty="Unknown",
                steps=[],
                layer_summary={}
            )
    
    @staticmethod
    def _generate_step_instructions(
        step_number: int,
        layer_z: int,
        layer_num: int,
        bricks: List[Dict],
        piece_counts: Dict[str, int]
    ) -> str:
        """
        Generate human-readable instructions for a single step.
        
        Args:
            step_number: Step number
            layer_z: Z coordinate (height) of layer
            layer_num: Layer number (1-indexed)
            bricks: List of bricks in this step
            piece_counts: Count of each piece type
            
        Returns:
            Formatted instruction string
        """
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"STEP {step_number}: BUILD LAYER {layer_num} (Height: {layer_z})")
        lines.append(f"{'='*60}")
        
        # Parts needed
        lines.append("\nParts needed for this step:")
        for part_id, qty in sorted(piece_counts.items()):
            lines.append(f"  • {part_id}: {qty} piece(s)")
        
        # Placement instructions
        lines.append(f"\nPlace {len(bricks)} bricks as follows:")
        
        # Sort bricks by position for logical ordering
        sorted_bricks = sorted(bricks, key=lambda b: (b.get("position", [0, 0, 0])[0], b.get("position", [0, 0, 0])[1]))
        
        for idx, brick in enumerate(sorted_bricks, 1):
            pos = brick.get("position", [0, 0, 0])
            part_id = brick.get("part_id")
            rotation = brick.get("rotation", 0)
            color_id = brick.get("color_id", 16)
            
            lines.append(f"  {idx}. Brick {part_id} at position ({pos[0]}, {pos[1]}, {pos[2]}), rotation {rotation}°")
        
        lines.append(f"\n✓ Total bricks in this step: {len(bricks)}")
        lines.append(f"{'='*60}")
        
        return "\n".join(lines)
    
    @staticmethod
    def export_to_text(guide: BuildGuide) -> str:
        """
        Export complete guide as formatted text document.
        
        Args:
            guide: BuildGuide object
            
        Returns:
            Formatted text string suitable for printing
        """
        lines = []
        
        # Header
        lines.append("╔" + "═" * 58 + "╗")
        lines.append("║" + " " * 15 + "LEGO BUILD INSTRUCTION MANUAL" + " " * 14 + "║")
        lines.append("╚" + "═" * 58 + "╝")
        
        # Project info
        lines.append(f"\nProject: {guide.project_name}")
        lines.append(f"Total Bricks: {guide.total_bricks}")
        lines.append(f"Total Steps: {guide.total_steps}")
        lines.append(f"Estimated Time: {guide.estimated_time_minutes} minutes")
        lines.append(f"Difficulty Level: {guide.difficulty}")
        
        # Layer summary
        lines.append("\n" + "─" * 60)
        lines.append("LAYER OVERVIEW")
        lines.append("─" * 60)
        for z in sorted(guide.layer_summary.keys()):
            lines.append(f"  {guide.layer_summary[z]}")
        
        # Steps
        lines.append("\n" + "═" * 60)
        lines.append("DETAILED BUILD STEPS")
        lines.append("═" * 60)
        
        for step in guide.steps:
            lines.append(step.instructions)
        
        # Completion message
        lines.append("\n" + "╔" + "═" * 58 + "╗")
        lines.append("║" + " " * 20 + "BUILD COMPLETE! ✓" + " " * 20 + "║")
        lines.append("╚" + "═" * 58 + "╝\n")
        
        return "\n".join(lines)
    
    @staticmethod
    def export_to_html(guide: BuildGuide) -> str:
        """
        Export complete guide as HTML document.
        
        Args:
            guide: BuildGuide object
            
        Returns:
            HTML formatted string
        """
        html = []
        
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append("  <title>LEGO Build Instructions - " + guide.project_name + "</title>")
        html.append("  <style>")
        html.append("    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }")
        html.append("    .header { background: #e74c3c; color: white; padding: 20px; border-radius: 5px; text-align: center; }")
        html.append("    .info { background: white; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 5px solid #3498db; }")
        html.append("    .step { background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }")
        html.append("    .step-title { color: #e74c3c; font-size: 18px; font-weight: bold; margin-bottom: 10px; }")
        html.append("    .parts-list { background: #ecf0f1; padding: 10px; border-radius: 3px; margin: 10px 0; }")
        html.append("    .brick-item { font-family: monospace; margin: 5px 0; }")
        html.append("    .complete { color: #27ae60; font-weight: bold; text-align: center; padding: 20px; font-size: 24px; }")
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")
        
        # Header
        html.append(f"  <div class='header'>")
        html.append(f"    <h1>LEGO BUILD INSTRUCTIONS</h1>")
        html.append(f"    <p>{guide.project_name}</p>")
        html.append(f"  </div>")
        
        # Project info
        html.append(f"  <div class='info'>")
        html.append(f"    <h2>Project Details</h2>")
        html.append(f"    <p><strong>Total Bricks:</strong> {guide.total_bricks}</p>")
        html.append(f"    <p><strong>Total Steps:</strong> {guide.total_steps}</p>")
        html.append(f"    <p><strong>Estimated Time:</strong> {guide.estimated_time_minutes} minutes</p>")
        html.append(f"    <p><strong>Difficulty:</strong> {guide.difficulty}</p>")
        html.append(f"  </div>")
        
        # Steps
        for step in guide.steps:
            html.append(f"  <div class='step'>")
            html.append(f"    <div class='step-title'>Step {step.step_number}: Layer {step.layer_z}</div>")
            html.append(f"    <div class='parts-list'>")
            html.append(f"      <strong>Parts needed:</strong><br>")
            for part_id, qty in sorted(step.piece_counts.items()):
                html.append(f"      <div class='brick-item'>• {part_id}: {qty} piece(s)</div>")
            html.append(f"    </div>")
            html.append(f"    <p><strong>Placement instructions:</strong></p>")
            html.append(f"    <ol>")
            sorted_bricks = sorted(step.bricks_in_step, key=lambda b: (b.get("position", [0, 0, 0])[0], b.get("position", [0, 0, 0])[1]))
            for brick in sorted_bricks:
                pos = brick.get("position", [0, 0, 0])
                part_id = brick.get("part_id")
                rotation = brick.get("rotation", 0)
                html.append(f"      <li>Place brick {part_id} at ({pos[0]}, {pos[1]}, {pos[2]}), rotation {rotation}°</li>")
            html.append(f"    </ol>")
            html.append(f"  </div>")
        
        # Completion
        html.append(f"  <div class='complete'>✓ BUILD COMPLETE!</div>")
        
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
    
    @staticmethod
    def export_to_json(guide: BuildGuide) -> Dict:
        """
        Export guide as structured JSON.
        
        Args:
            guide: BuildGuide object
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "project_name": guide.project_name,
            "total_steps": guide.total_steps,
            "total_bricks": guide.total_bricks,
            "estimated_time_minutes": guide.estimated_time_minutes,
            "difficulty": guide.difficulty,
            "layers": guide.layer_summary,
            "steps": [
                {
                    "step_number": step.step_number,
                    "layer_z": step.layer_z,
                    "piece_count": step.piece_counts,
                    "brick_count": len(step.bricks_in_step),
                    "bricks": step.bricks_in_step
                }
                for step in guide.steps
            ]
        }
