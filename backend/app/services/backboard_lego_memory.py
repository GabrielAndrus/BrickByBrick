"""
Backboard Memory Integration for LEGO Build System
Provides persistent cross-session memory using Backboard.io pattern.
Stores build histories, component designs, and user preferences.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class BuildMemoryEntry:
    """Single build memory entry"""
    build_id: str
    project_name: str
    user_id: str
    voxel_data: Dict  # Original Three.js voxel input
    manifest: Dict    # Generated LEGO manifest
    piece_summary: Dict  # Piece count summary
    components: List[Dict]  # Saved components
    creation_date: str
    room_type: str  # bedroom, office, living room, etc.
    metadata: Dict  # Custom metadata
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "build_id": self.build_id,
            "project_name": self.project_name,
            "user_id": self.user_id,
            "voxel_data": self.voxel_data,
            "manifest": self.manifest,
            "piece_summary": self.piece_summary,
            "components": self.components,
            "creation_date": self.creation_date,
            "room_type": self.room_type,
            "metadata": self.metadata
        }


class BackboardLegoMemory:
    """
    Backboard-style stateful memory for LEGO builds.
    Maintains build history and component library.
    """
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize Backboard memory.
        
        Args:
            user_id: Unique user identifier
        """
        self.user_id = user_id
        self.builds: Dict[str, BuildMemoryEntry] = {}
        self.component_library: Dict[str, Dict] = {}
        self.user_preferences: Dict[str, Any] = {
            "preferred_colors": [],
            "preferred_styles": [],
            "reuse_similar_components": True,
            "max_unique_parts": None
        }
    
    def save_build(
        self,
        project_name: str,
        voxel_data: Dict,
        manifest: Dict,
        piece_summary: Dict,
        components: List[Dict],
        room_type: str = "generic",
        metadata: Dict = None
    ) -> str:
        """
        Save a build to memory.
        
        Args:
            project_name: Name of project
            voxel_data: Original Three.js voxels
            manifest: Generated LEGO manifest
            piece_summary: Piece count results
            components: Saved components used
            room_type: Type of room
            metadata: Additional metadata
            
        Returns:
            Build ID
        """
        try:
            build_id = str(uuid.uuid4())
            
            entry = BuildMemoryEntry(
                build_id=build_id,
                project_name=project_name,
                user_id=self.user_id,
                voxel_data=voxel_data,
                manifest=manifest,
                piece_summary=piece_summary,
                components=components,
                creation_date=datetime.now().isoformat(),
                room_type=room_type,
                metadata=metadata or {}
            )
            
            self.builds[build_id] = entry
            
            logger.info(f"Saved build {build_id} to Backboard memory: {project_name}")
            return build_id
        
        except Exception as e:
            logger.error(f"Error saving build: {e}")
            return None
    
    def get_build(self, build_id: str) -> Optional[BuildMemoryEntry]:
        """Get a build from memory"""
        return self.builds.get(build_id)
    
    def get_builds_by_room(self, room_type: str) -> List[BuildMemoryEntry]:
        """Get all builds for a specific room type"""
        return [
            build for build in self.builds.values()
            if build.room_type == room_type
        ]
    
    def get_recent_builds(self, limit: int = 10) -> List[BuildMemoryEntry]:
        """Get recent builds"""
        builds = sorted(
            self.builds.values(),
            key=lambda b: b.creation_date,
            reverse=True
        )
        return builds[:limit]
    
    def add_to_component_library(
        self,
        component_id: str,
        component_type: str,
        brick_composition: Dict[str, int],
        dimensions: Tuple,
        metadata: Dict = None
    ) -> bool:
        """
        Add component to reusable library.
        
        Args:
            component_id: Unique ID
            component_type: Type (desk, chair, etc.)
            brick_composition: Parts dict
            dimensions: (width, depth, height)
            metadata: Additional info
            
        Returns:
            True if successful
        """
        try:
            self.component_library[component_id] = {
                "component_type": component_type,
                "brick_composition": brick_composition,
                "dimensions": dimensions,
                "added_date": datetime.now().isoformat(),
                "usage_count": 0,
                "metadata": metadata or {}
            }
            
            logger.info(f"Added component to library: {component_id} ({component_type})")
            return True
        
        except Exception as e:
            logger.error(f"Error adding to library: {e}")
            return False
    
    def get_library_component(self, component_id: str) -> Optional[Dict]:
        """Get component from library"""
        return self.component_library.get(component_id)
    
    def get_library_by_type(self, component_type: str) -> Dict[str, Dict]:
        """Get all components of a type from library"""
        return {
            cid: comp for cid, comp in self.component_library.items()
            if comp.get("component_type") == component_type
        }
    
    def update_preferences(self, preferences: Dict) -> bool:
        """Update user preferences"""
        try:
            self.user_preferences.update(preferences)
            logger.info(f"Updated user preferences for {self.user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get memory statistics"""
        builds_by_room = {}
        for build in self.builds.values():
            if build.room_type not in builds_by_room:
                builds_by_room[build.room_type] = 0
            builds_by_room[build.room_type] += 1
        
        components_by_type = {}
        for comp in self.component_library.values():
            comp_type = comp.get("component_type")
            if comp_type not in components_by_type:
                components_by_type[comp_type] = 0
            components_by_type[comp_type] += 1
        
        return {
            "user_id": self.user_id,
            "total_builds": len(self.builds),
            "builds_by_room": builds_by_room,
            "total_library_components": len(self.component_library),
            "components_by_type": components_by_type,
            "user_preferences": self.user_preferences
        }
    
    def export_memory(self, filepath: str) -> bool:
        """Export all memory to JSON file"""
        try:
            data = {
                "user_id": self.user_id,
                "builds": [build.to_dict() for build in self.builds.values()],
                "component_library": self.component_library,
                "user_preferences": self.user_preferences,
                "export_date": datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported Backboard memory to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting memory: {e}")
            return False
    
    def import_memory(self, filepath: str) -> bool:
        """Import memory from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.user_id = data.get("user_id", self.user_id)
            
            # Import builds
            self.builds.clear()
            for build_data in data.get("builds", []):
                entry = BuildMemoryEntry(
                    build_id=build_data.get("build_id"),
                    project_name=build_data.get("project_name"),
                    user_id=build_data.get("user_id"),
                    voxel_data=build_data.get("voxel_data", {}),
                    manifest=build_data.get("manifest", {}),
                    piece_summary=build_data.get("piece_summary", {}),
                    components=build_data.get("components", []),
                    creation_date=build_data.get("creation_date"),
                    room_type=build_data.get("room_type", "generic"),
                    metadata=build_data.get("metadata", {})
                )
                self.builds[entry.build_id] = entry
            
            # Import components
            self.component_library = data.get("component_library", {})
            
            # Import preferences
            self.user_preferences.update(data.get("user_preferences", {}))
            
            logger.info(f"Imported Backboard memory from {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error importing memory: {e}")
            return False
    
    def get_similar_builds(
        self,
        project_name: str,
        room_type: str = None,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Find similar builds based on name and room type.
        
        Args:
            project_name: Name to search for
            room_type: Filter by room type
            max_results: Max results
            
        Returns:
            List of similar builds
        """
        results = []
        
        for build in self.builds.values():
            # Filter by room type if provided
            if room_type and build.room_type != room_type:
                continue
            
            # Simple name similarity (could use fuzzy matching)
            name_lower = project_name.lower()
            build_name_lower = build.project_name.lower()
            
            similarity = 0.0
            if name_lower in build_name_lower or build_name_lower in name_lower:
                similarity = 0.8
            
            if similarity > 0:
                results.append({
                    "build_id": build.build_id,
                    "project_name": build.project_name,
                    "room_type": build.room_type,
                    "creation_date": build.creation_date,
                    "total_bricks": build.piece_summary.get("total_pieces", 0),
                    "similarity": similarity
                })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_results]


class LegoBuildOrchestrator:
    """
    Orchestrates build generation with Backboard memory integration.
    Coordinates MasterBuilder, vector database, and Backboard memory.
    """
    
    def __init__(self, user_id: str = "default"):
        """Initialize orchestrator"""
        self.backboard = BackboardLegoMemory(user_id)
        self.user_id = user_id
    
    def generate_build_with_memory(
        self,
        three_js_voxels: Dict,
        project_name: str,
        room_type: str = "generic",
        master_builder=None,
        vector_db=None,
        reuse_components: bool = True
    ) -> Dict:
        """
        Generate build with memory integration.
        
        Args:
            three_js_voxels: Three.js voxel data
            project_name: Project name
            room_type: Room type
            master_builder: MasterBuilder instance
            vector_db: VectorLegoDatabase instance
            reuse_components: Whether to suggest reused components
            
        Returns:
            Complete build package
        """
        try:
            # Process build
            if not master_builder:
                logger.error("MasterBuilder required")
                return {}
            
            manifest = master_builder.process_voxels_sync(three_js_voxels)
            piece_count = master_builder.get_piece_count()
            
            # Get recommendations if enabled
            recommendations = []
            if reuse_components and vector_db:
                # Placeholder for component recommendations
                logger.debug("Component recommendations calculated")
            
            # Build package
            build_package = {
                "project_name": project_name,
                "room_type": room_type,
                "manifest": manifest,
                "piece_count": piece_count.total_pieces,
                "estimated_cost": piece_count.estimated_cost,
                "recommendations": recommendations,
                "generation_date": datetime.now().isoformat()
            }
            
            # Save to Backboard memory
            build_id = self.backboard.save_build(
                project_name=project_name,
                voxel_data=three_js_voxels,
                manifest=manifest,
                piece_summary={
                    "total_pieces": piece_count.total_pieces,
                    "total_unique": piece_count.total_unique_pieces,
                    "cost": piece_count.estimated_cost
                },
                components=recommendations,
                room_type=room_type
            )
            
            build_package["build_id"] = build_id
            
            logger.info(f"Generated build {build_id} with memory integration")
            return build_package
        
        except Exception as e:
            logger.error(f"Error in build orchestration: {e}")
            return {}
    
    def get_user_statistics(self) -> Dict:
        """Get user statistics from Backboard"""
        return self.backboard.get_statistics()
