"""
Master Builder Service
Implements Greedy Fitting Algorithm for LEGO bricks.

Takes a 3D array of voxels (x, y, z, hex_color) from Three.js and converts it
into a list of real LEGO bricks with proper structural integrity.
"""
import logging
import asyncio
import os
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass
import json

from app.services.rebrickable_api import get_rebrickable_client
from app.services.part_discovery import get_part_discovery_service

logger = logging.getLogger(__name__)


@dataclass
class Voxel:
    """Represents a single voxel from Three.js input"""
    x: int
    y: int
    z: int
    hex_color: str


@dataclass
class PlacedBrick:
    """Represents a placed LEGO brick in the final manifest"""
    part_id: str
    position: Tuple[int, int, int]  # (x, y, z)
    rotation: int  # Rotation in degrees: 0, 90, 180, 270
    color_id: int  # Rebrickable color ID
    is_verified: bool = False  # Whether part availability was verified


class MasterBuilder:
    """
    Master Builder Service implementing Greedy Fitting Algorithm.
    
    Core Features:
    1. Greedy Volume Fitting - Tries largest bricks first (sorted by area: 2x12, 2x10, 2x8, etc.)
       - Optimizes for minimal part count by prioritizing larger bricks
       - Supports 40+ common LEGO brick types (bricks, plates, tiles)
       - Automatically sorts by volume (width * height) descending
    2. Laminar Interlocking - Stagger bricks on even vs odd layers
    3. Color Verification - Uses Rebrickable API to verify part availability
    4. Fallback Logic - If a brick is unavailable, tries next smaller size
    """
    
    # Dynamic brick priorities - discovered via Rebrickable/Backboard APIs
    # Format: List of (width, height, depth, part_id, priority_score)
    # Populated dynamically based on voxel shape analysis
    _brick_priorities_cache: Optional[List[Tuple[int, int, int, str, float]]] = None
    
    # Rotation options (in degrees)
    ROTATIONS = [0, 90, 180, 270]
    
    def __init__(self):
        # 3D Grid: (x, y, z) -> hex_color or None
        self.voxel_grid: Dict[Tuple[int, int, int], str] = {}
        
        # Placed bricks
        self.placed_bricks: List[PlacedBrick] = []
        
        # Occupied positions (for collision detection)
        self.occupied_positions: Set[Tuple[int, int, int]] = set()
        
        # Layer tracking for interlocking
        self.layer_bricks: Dict[int, List[PlacedBrick]] = defaultdict(list)
        
        # Color mapping: hex -> Rebrickable color_id
        self.color_cache: Dict[str, int] = {}
        
        # Rebrickable API client
        self.rebrickable = get_rebrickable_client()
        
        # Part Discovery Service (for intelligent part selection)
        self.part_discovery = get_part_discovery_service()
        
        # Search mode: "simple" (Rebrickable only) or "hard" (Backboard AI)
        self.search_mode = os.getenv("PART_SEARCH_MODE", "simple").lower()
    
    async def _initialize_brick_priorities(self):
        """
        Initialize brick priorities from Rebrickable API.
        This fetches parts dynamically and calculates priority scores.
        """
        if self._brick_priorities is None:
            logger.info("Initializing dynamic brick priorities from Rebrickable API...")
            self._brick_priorities = await self.rebrickable.fetch_brick_priorities(
                include_categories=["Bricks", "Plates", "Tiles", "Bricks Round and Cones", "Bricks Curved"],
                exclude_tags=["minifig", "rare", "expensive", "sticker"],
                min_area=1,
                max_results=200
            )
            logger.info(f"Initialized {len(self._brick_priorities)} brick types with dynamic priorities")
    
    async def process_voxels(self, voxel_data: List[Dict]) -> Dict:
        """
        Main entry point: Process voxel JSON and generate MasterManifest.
        
        Args:
            voxel_data: List of dicts with keys: x, y, z, hex_color
            
        Returns:
            MasterManifest JSON containing Part ID, Position, Rotation, Color ID, and is_verified
        """
        logger.info(f"Processing {len(voxel_data)} voxels")
        
        # Reset state
        self.voxel_grid = {}
        self.placed_bricks = []
        self.occupied_positions = set()
        self.layer_bricks = defaultdict(list)
        self.color_cache = {}
        
        # Load voxels into grid
        for voxel in voxel_data:
            x = int(voxel.get("x", 0))
            y = int(voxel.get("y", 0))
            z = int(voxel.get("z", 0))
            hex_color = voxel.get("hex_color", "#FFFFFF")
            self.voxel_grid[(x, y, z)] = hex_color
        
        if not self.voxel_grid:
            logger.warning("No voxels to process")
            return self._generate_manifest()
        
        # Process layer by layer with laminar interlocking
        min_z = min(z for _, _, z in self.voxel_grid.keys())
        max_z = max(z for _, _, z in self.voxel_grid.keys())
        
        for z in range(min_z, max_z + 1):
            layer_voxels = {
                (x, y): hex_color
                for (x, y, z_pos), hex_color in self.voxel_grid.items()
                if z_pos == z
            }
            
            if layer_voxels:
                await self._process_layer(z, layer_voxels)
        
        # Generate final manifest
        return self._generate_manifest()
    
    def process_voxels_sync(self, voxel_data: List[Dict]) -> Dict:
        """
        Synchronous wrapper for process_voxels.
        For backward compatibility with non-async code.
        """
        return asyncio.run(self.process_voxels(voxel_data))
    
    async def _process_layer(self, layer_z: int, layer_voxels: Dict[Tuple[int, int], str]):
        """
        Process a single layer with laminar interlocking and Rebrickable verification.
        
        Laminar Interlocking: Stagger brick positions on even vs odd layers
        so seams do not align vertically.
        - Even layers (z=0, 2, 4...): Bricks align to even grid positions
        - Odd layers (z=1, 3, 5...): Bricks align to odd grid positions
        """
        logger.info(f"Processing layer {layer_z} with {len(layer_voxels)} voxels")
        
        # Group voxels by color
        color_groups: Dict[str, Set[Tuple[int, int]]] = defaultdict(set)
        for (x, y), hex_color in layer_voxels.items():
            color_groups[hex_color].add((x, y))
        
        # Process each color group
        for hex_color, voxel_set in color_groups.items():
            # Get closest LEGO color for this hex
            color_id = await self.rebrickable.get_closest_lego_color(hex_color)
            logger.debug(f"Hex {hex_color} mapped to Rebrickable color ID {color_id}")
            
            # Analyze shape characteristics
            shape_analysis = self.part_discovery.analyze_voxel_shape(voxel_set)
            logger.debug(f"Shape analysis: round={shape_analysis.get('is_round')}, "
                        f"curved={shape_analysis.get('is_curved')}, "
                        f"rectangular={shape_analysis.get('is_rectangular')}")
            
            # Discover appropriate parts for this shape
            use_hard_search = (self.search_mode == "hard")
            discovered_parts = await self.part_discovery.discover_parts_for_shape(
                shape_analysis, color_id, use_hard_search
            )
            
            if not discovered_parts:
                logger.warning(f"No parts discovered for shape, using fallback")
                discovered_parts = self._get_fallback_parts(color_id)
            
            # Greedy fitting for this color group with fallback logic
            remaining_voxels = voxel_set.copy()
            
            # Try each discovered part in priority order (sorted by area)
            for part_info in discovered_parts:
                if not remaining_voxels:
                    break
                
                part_id = part_info.get("part_num", "")
                width = part_info.get("width", 1)
                height = part_info.get("height", 1)
                depth = 1  # Default depth (can be enhanced later)
                
                # Try all rotations for this brick size
                for rotation in self.ROTATIONS:
                    if not remaining_voxels:
                        break
                    
                    # Get rotated dimensions
                    rot_width, rot_height = self._get_rotated_dimensions(
                        width, height, rotation
                    )
                    
                    # Find best placement with verification
                    placed = await self._greedy_place_bricks_with_verification(
                        remaining_voxels,
                        rot_width,
                        rot_height,
                        part_id,
                        hex_color,
                        color_id,
                        layer_z,
                        rotation
                    )
                    
                    # Remove placed voxels
                    for brick in placed:
                        occupied = self._get_brick_occupied_positions(
                            brick.position, rot_width, rot_height, layer_z
                        )
                        # Convert 3D positions back to 2D for removal
                        occupied_2d = {(x, y) for x, y, z in occupied}
                        remaining_voxels -= occupied_2d
    
    async def _greedy_place_bricks_with_verification(
        self,
        voxels: Set[Tuple[int, int]],
        width: int,
        height: int,
        part_id: str,
        hex_color: str,
        color_id: int,
        layer_z: int,
        rotation: int
    ) -> List[PlacedBrick]:
        """
        Greedy placement with Rebrickable verification.
        Only places bricks that are verified to be available in the specified color.
        Implements fallback: if a brick is unavailable, it will be skipped and
        the next smallest brick size will be tried.
        """
        placed = []
        remaining = voxels.copy()
        
        # Laminar interlocking: Ensure brick positions align to grid
        # Even layers: positions must be even-aligned
        # Odd layers: positions must be odd-aligned
        is_even_layer = (layer_z % 2 == 0)
        
        # Verify part availability once (cache result)
        is_available = await self.rebrickable.verify_part_availability(part_id, color_id)
        
        if not is_available:
            logger.warning(
                f"Part {part_id} not available in color {color_id}, "
                f"skipping this brick size (will try next smaller size)"
            )
            return []  # Return empty list to trigger fallback to next brick size
        
        # Sort voxels for consistent placement order
        sorted_voxels = sorted(remaining)
        
        for x, y in sorted_voxels:
            # Apply laminar interlocking: Prefer positions that stagger seams
            # Even layers: prefer even-aligned positions
            # Odd layers: prefer odd-aligned positions
            # This ensures seams don't align vertically between layers
            if is_even_layer:
                # Even layer: prefer even starting positions (but allow others if needed)
                # Skip if position doesn't align (for strict interlocking)
                if (x % 2 != 0) or (y % 2 != 0):
                    continue
            else:
                # Odd layer: prefer odd starting positions
                # Skip if position doesn't align (for strict interlocking)
                if (x % 2 != 1) or (y % 2 != 1):
                    continue
            
            # Check if we can place a brick starting at this position
            if self._can_place_brick_at(x, y, layer_z, width, height):
                # Verify all required positions are in the voxel set
                required_positions = self._get_rectangular_positions(x, y, width, height)
                if required_positions.issubset(remaining):
                    # Place the brick (already verified as available)
                    brick = PlacedBrick(
                        part_id=part_id,
                        position=(x, y, layer_z),
                        rotation=rotation,
                        color_id=color_id,
                        is_verified=True  # Verified before placement
                    )
                    
                    self.placed_bricks.append(brick)
                    self.layer_bricks[layer_z].append(brick)
                    
                    # Mark positions as occupied
                    occupied = self._get_brick_occupied_positions(
                        (x, y, layer_z), width, height, layer_z
                    )
                    self.occupied_positions.update(occupied)
                    remaining -= required_positions
                    placed.append(brick)
        
        return placed
    
    def _can_place_brick_at(
        self, x: int, y: int, z: int, width: int, height: int
    ) -> bool:
        """Check if a brick can be placed at the given position"""
        positions = self._get_brick_occupied_positions((x, y, z), width, height, z)
        return not any(pos in self.occupied_positions for pos in positions)
    
    def _get_rectangular_positions(
        self, start_x: int, start_y: int, width: int, height: int
    ) -> Set[Tuple[int, int]]:
        """Get all 2D positions that a rectangular brick would occupy"""
        positions = set()
        for dx in range(width):
            for dy in range(height):
                positions.add((start_x + dx, start_y + dy))
        return positions
    
    def _get_brick_occupied_positions(
        self, position: Tuple[int, int, int], width: int, height: int, z: int
    ) -> Set[Tuple[int, int, int]]:
        """Get all 3D positions that a brick occupies"""
        x, y, _ = position
        positions = set()
        for dx in range(width):
            for dy in range(height):
                positions.add((x + dx, y + dy, z))
        return positions
    
    def _get_rotated_dimensions(
        self, width: int, height: int, rotation: int
    ) -> Tuple[int, int]:
        """Get dimensions after rotation (90 or 270 swaps width/height)"""
        if rotation in [90, 270]:
            return (height, width)
        return (width, height)
    
    
    def _generate_manifest(self) -> Dict:
        """
        Generate MasterManifest JSON output.
        
        Returns JSON containing:
        - Part ID
        - Position (x, y, z)
        - Rotation
        - Color ID
        """
        manifest = {
            "manifest_version": "1.0",
            "total_bricks": len(self.placed_bricks),
            "bricks": []
        }
        
        # Add each brick to manifest
        for brick in self.placed_bricks:
            manifest["bricks"].append({
                "part_id": brick.part_id,
                "position": list(brick.position),  # Convert tuple to list for JSON
                "rotation": brick.rotation,
                "color_id": brick.color_id,
                "is_verified": brick.is_verified
            })
        
        # Add layer statistics
        manifest["layers"] = {
            layer: len(bricks) for layer, bricks in self.layer_bricks.items()
        }
        
        # Add inventory summary
        inventory = defaultdict(int)
        for brick in self.placed_bricks:
            key = f"{brick.part_id}_{brick.color_id}"
            inventory[key] += 1
        
        manifest["inventory"] = [
            {
                "part_id": part_id.split("_")[0],
                "color_id": int(part_id.split("_")[1]),
                "quantity": count
            }
            for part_id, count in inventory.items()
        ]
        
        logger.info(f"Generated manifest with {len(self.placed_bricks)} bricks")
        return manifest
    
    def _get_fallback_parts(self, color_id: int) -> List[Dict]:
        """Fallback parts list when dynamic discovery fails."""
        return [
            {"part_num": "3001", "width": 4, "height": 2, "area": 8, "color_id": color_id, "is_verified": False},
            {"part_num": "3003", "width": 2, "height": 2, "area": 4, "color_id": color_id, "is_verified": False},
            {"part_num": "3004", "width": 2, "height": 1, "area": 2, "color_id": color_id, "is_verified": False},
            {"part_num": "3005", "width": 1, "height": 1, "area": 1, "color_id": color_id, "is_verified": False},
        ]
    
    def get_manifest_json(self) -> str:
        """Get manifest as JSON string"""
        manifest = self._generate_manifest()
        return json.dumps(manifest, indent=2)
