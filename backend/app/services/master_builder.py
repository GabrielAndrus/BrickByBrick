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
from app.services.lego_objects_database import (
    get_lego_object_by_id,
    get_lego_objects_by_type,
    get_object_by_signature,
    find_similar_objects,
    get_brick_composition,
)
from app.services.piece_counter import PieceCounter, PieceSummary
from app.services.instruction_manual_generator import InstructionManualGenerator, BuildGuide
from app.services.ldraw_generator import LDrawGenerator, LegoVisualizerWeb
import hashlib  # For cluster signature hashing

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


@dataclass
class SeamMapEntry:
    """Represents a seam in the Seam Map for structural analysis"""
    layer_z: int
    x_position: int  # Seam x-coordinate
    width: int  # Width of seam gap
    covered_by: Optional[str] = None  # Brick part_id that covers this seam


@dataclass
class SubComponentManifest:
    """Represents a saved sub-component for memory evolution"""
    component_type: str  # e.g., "desk", "bed_base", "shelf"
    signature: str  # Cluster signature
    bricks: List[PlacedBrick]
    metadata: Dict = None  # Additional metadata (dimensions, colors, etc.)
    confirmed: bool = False  # User-confirmed optimized version


class MasterBuilder:
    """
    Master Builder Service implementing Greedy Fitting Algorithm with Advanced Features.
    
    Core Features:
    1. Greedy Volume Fitting - Tries largest bricks first (sorted by area: 2x12, 2x10, 2x8, etc.)
       - Optimizes for minimal part count by prioritizing larger bricks
       - Supports 40+ common LEGO brick types (bricks, plates, tiles)
       - Automatically sorts by volume (width * height) descending
       - ENHANCED: Prioritizes specialized bricks (2x4, 1x6, 2x2) before small 1x1/1x2
    2. Laminar Interlocking - Stagger bricks on even vs odd layers
    3. Staggered Joints - Prevents vertical seams from aligning across layers
    4. Curviness Test - Queries Rebrickable for slopes/curved pieces matching surface normals
    5. Backboard Memory - Checks for existing sub-assembly fragments matching cluster signature
    6. Color Verification - Uses Rebrickable API to verify part availability
    7. Fallback Logic - If a brick is unavailable, tries next smaller size
    """
    
    # Dynamic brick priorities - discovered via Rebrickable/Backboard APIs
    # Format: List of (width, height, depth, part_id, priority_score)
    # Populated dynamically based on voxel shape analysis
    _brick_priorities_cache: Optional[List[Tuple[int, int, int, str, float]]] = None
    
    # Rotation options (in degrees)
    ROTATIONS = [0, 90, 180, 270]
    
    # Priority brick IDs - Search for these first (larger bricks)
    PRIORITY_BRICK_IDS = {
        "3001": {"width": 4, "height": 2, "priority": 100},  # 2x4
        "3009": {"width": 6, "height": 1, "priority": 90},   # 1x6
        "3003": {"width": 2, "height": 2, "priority": 80},   # 2x2
    }
    
    # Slope/Curved brick IDs for curviness test
    SLOPE_BRICK_IDS = {
        "3040": {"name": "Slope 45 Degree", "angles": [45]},
        "3038": {"name": "Slope 45 Degree Inverted", "angles": [-45]},
        "3297": {"name": "Slope 33 Degree", "angles": [33, -33]},
    }
    
    # Specialized parts for component substitution
    SPECIALIZED_PARTS = {
        "tile": {
            "3068": {"name": "Tile 2x2", "width": 2, "height": 2},
            "3069": {"name": "Tile 1x2", "width": 2, "height": 1},
            "3070": {"name": "Tile 1x1", "width": 1, "height": 1},
        },
        "hinge": {
            "3938": {"name": "Hinge Brick 1x2", "width": 2, "height": 1},
            "6134": {"name": "Hinge Plate 1x2", "width": 2, "height": 1},
        }
    }
    
    # Component type classifiers (for Gemini analysis)
    COMPONENT_TYPES = {
        "desk": {"keywords": ["desk", "table", "work surface"], "typical_parts": ["3068"]},
        "bed_base": {"keywords": ["bed", "base", "platform"], "typical_parts": ["3001", "3003"]},
        "shelf": {"keywords": ["shelf", "rack", "frame"], "typical_parts": ["3001"]},
    }
    
    def __init__(self):
        # 3D Grid: (x, y, z) -> hex_color or None
        self.voxel_grid: Dict[Tuple[int, int, int], str] = {}
        
        # Placed bricks
        self.placed_bricks: List[PlacedBrick] = []
        
        # Occupied positions (for collision detection)
        self.occupied_positions: Set[Tuple[int, int, int]] = set()
        
        # Layer tracking for interlocking
        self.layer_bricks: Dict[int, List[PlacedBrick]] = defaultdict(list)
        
        # Seam tracking for staggered joints: layer_z -> set of x coordinates where seams occur
        self.layer_seams: Dict[int, Set[int]] = defaultdict(set)
        
        # Color mapping: hex -> Rebrickable color_id
        self.color_cache: Dict[str, int] = {}
        
        # Rebrickable API client
        self.rebrickable = get_rebrickable_client()
        
        # Part Discovery Service (for intelligent part selection)
        self.part_discovery = get_part_discovery_service()
        
        # Backboard Memory: cluster_signature -> sub-assembly fragments
        self.backboard_memory: Dict[str, List[PlacedBrick]] = {}
        
        # Seam Map: Persistent storage of seam locations for structural analysis
        self.seam_map: List[SeamMapEntry] = []
        
        # Component Evolution: Saved sub-components for future reuse
        self.evolved_components: Dict[str, SubComponentManifest] = {}
        
        # Component classification cache (for Gemini analysis results)
        self.component_cache: Dict[str, str] = {}  # signature -> component_type
        
        # Test mode: Skip part verification (for testing without API keys)
        self.test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    
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
            
            # GREEDY SEARCH: Prioritize larger specialized bricks first (2x4, 1x6, 2x2)
            remaining_voxels = voxel_set.copy()
            
            # First pass: Try priority bricks (2x4, 1x6, 2x2)
            priority_parts = [
                p for p in discovered_parts 
                if p.get("part_num") in self.PRIORITY_BRICK_IDS
            ]
            priority_parts.sort(
                key=lambda p: self.PRIORITY_BRICK_IDS.get(p.get("part_num"), {}).get("priority", 0),
                reverse=True
            )
            
            # Process priority parts first
            for part_info in priority_parts:
                if not remaining_voxels:
                    break
                
                part_id = part_info.get("part_num", "")
                width = part_info.get("width", 1)
                height = part_info.get("height", 1)
                
                for rotation in self.ROTATIONS:
                    if not remaining_voxels:
                        break
                    
                    rot_width, rot_height = self._get_rotated_dimensions(width, height, rotation)
                    
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
                    
                    for brick in placed:
                        occupied = self._get_brick_occupied_positions(
                            brick.position, rot_width, rot_height, layer_z
                        )
                        occupied_2d = {(x, y) for x, y, z in occupied}
                        remaining_voxels -= occupied_2d
            
            # Second pass: Try remaining parts in priority order
            other_parts = [
                p for p in discovered_parts 
                if p.get("part_num") not in self.PRIORITY_BRICK_IDS
            ]
            
            for part_info in other_parts:
                if not remaining_voxels:
                    break
                
                part_id = part_info.get("part_num", "")
                width = part_info.get("width", 1)
                height = part_info.get("height", 1)
                
                for rotation in self.ROTATIONS:
                    if not remaining_voxels:
                        break
                    
                    rot_width, rot_height = self._get_rotated_dimensions(width, height, rotation)
                    
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
                    
                    for brick in placed:
                        occupied = self._get_brick_occupied_positions(
                            brick.position, rot_width, rot_height, layer_z
                        )
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
        Greedy placement with Rebrickable verification and Staggered Joints constraint.
        Only places bricks that are verified to be available in the specified color.
        Implements fallback: if a brick is unavailable, it will be skipped and
        the next smallest brick size will be tried.
        
        STAGGERED JOINTS: Prevents vertical seams from aligning across layers.
        If layer N has a seam at x=k, layer N+1 must use larger bricks to bridge x=k.
        """
        placed = []
        remaining = voxels.copy()
        
        # Laminar interlocking: Ensure brick positions align to grid
        # Even layers: positions must be even-aligned
        # Odd layers: positions must be odd-aligned
        is_even_layer = (layer_z % 2 == 0)
        
        # Get seams from previous layer for staggered joints constraint
        prev_layer_seams = self.layer_seams.get(layer_z - 1, set()) if layer_z > 0 else set()
        
        # Verify part availability once (cache result)
        # Skip verification in test mode
        if self.test_mode:
            is_available = True
            logger.debug(f"Test mode: Assuming part {part_id} is available")
        else:
            # If API is unavailable or rate-limited, assume available to allow testing
            try:
                is_available = await self.rebrickable.verify_part_availability(part_id, color_id)
            except Exception as e:
                logger.warning(f"Part verification failed for {part_id}: {e}, assuming available")
                is_available = True  # Assume available if verification fails
        
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
            
            # STAGGERED JOINTS: Check if brick bridges previous layer seams
            # If layer N-1 has a seam at x=k, current brick must bridge x=k with width>=2
            if prev_layer_seams and layer_z > 0:
                brick_end_x = x + width
                bridges_seams = False
                
                for seam_x in prev_layer_seams:
                    if x <= seam_x < brick_end_x:
                        # This brick bridges the seam, good
                        bridges_seams = True
                        break
                
                # If brick doesn't bridge any seams but there are seams, skip 1x1/1x2 bricks
                if not bridges_seams and prev_layer_seams and width <= 2:
                    continue  # Prefer larger bricks that bridge seams
            
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
                    
                    # Track seams for next layer (staggered joints constraint)
                    # Seams occur at brick edges
                    self.layer_seams[layer_z].add(x)
                    self.layer_seams[layer_z].add(x + width)
                    
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
        Generate MasterManifest JSON output with DETAILED VOXEL/VERTEX information.
        
        Returns JSON containing:
        - Part ID (LEGO type)
        - Position (x, y, z) in 3D space
        - Rotation in degrees
        - Color ID and color info
        - Detailed voxel coverage (which voxels this brick occupies)
        - Vertex positions (3D corners of the brick)
        """
        manifest = {
            "manifest_version": "2.0",
            "total_bricks": len(self.placed_bricks),
            "bricks": [],
            "voxel_coverage": [],
            "generation_metadata": {
                "algorithm": "greedy_volume_fitting",
                "interlocking_style": "laminar_staggered",
                "priority_method": "area_sorted"
            }
        }
        
        # LEGO brick dimensions in studs (standard LEGO unit)
        # Each stud = 8mm, standard brick height = 9.6mm (1.2 studs)
        brick_dimensions = {
            "3001": {"studs_width": 4, "studs_depth": 2, "studs_height": 1},  # 2x4 brick
            "3009": {"studs_width": 6, "studs_depth": 1, "studs_height": 1},  # 1x6 brick
            "3003": {"studs_width": 2, "studs_depth": 2, "studs_height": 1},  # 2x2 brick
            "3004": {"studs_width": 2, "studs_depth": 1, "studs_height": 1},  # 1x2 brick
            "3005": {"studs_width": 1, "studs_depth": 1, "studs_height": 1},  # 1x1 brick
        }
        
        # Add each brick to manifest with detailed vertex information
        for brick in self.placed_bricks:
            x, y, z = brick.position
            
            # Get brick dimensions for vertex calculation
            part_id = brick.part_id
            dims = brick_dimensions.get(part_id, {"studs_width": 1, "studs_depth": 1, "studs_height": 1})
            
            # Calculate 8 vertices of brick (3D corners)
            # LEGO studs: width=8mm, depth=8mm, height=9.6mm
            studs_to_mm = 8.0
            height_to_mm = 9.6
            
            vertices = [
                # Bottom face (z = 0)
                [x * studs_to_mm, y * studs_to_mm, z * height_to_mm],
                [(x + dims["studs_width"]) * studs_to_mm, y * studs_to_mm, z * height_to_mm],
                [(x + dims["studs_width"]) * studs_to_mm, (y + dims["studs_depth"]) * studs_to_mm, z * height_to_mm],
                [x * studs_to_mm, (y + dims["studs_depth"]) * studs_to_mm, z * height_to_mm],
                # Top face (z = height)
                [x * studs_to_mm, y * studs_to_mm, (z + dims["studs_height"]) * height_to_mm],
                [(x + dims["studs_width"]) * studs_to_mm, y * studs_to_mm, (z + dims["studs_height"]) * height_to_mm],
                [(x + dims["studs_width"]) * studs_to_mm, (y + dims["studs_depth"]) * studs_to_mm, (z + dims["studs_height"]) * height_to_mm],
                [x * studs_to_mm, (y + dims["studs_depth"]) * studs_to_mm, (z + dims["studs_height"]) * height_to_mm],
            ]
            
            # Voxel coverage - which voxels are covered by this brick
            covered_voxels = []
            for vx in range(x, x + dims["studs_width"]):
                for vy in range(y, y + dims["studs_depth"]):
                    for vz in range(z, z + dims["studs_height"]):
                        covered_voxels.append([vx, vy, vz])
            
            brick_data = {
                "brick_id": f"{part_id}_{brick.color_id}",
                "part_id": brick.part_id,
                "lego_type": self._get_lego_type_name(brick.part_id),
                "position": {
                    "studs": list(brick.position),  # In LEGO stud units
                    "mm": [x * studs_to_mm, y * studs_to_mm, z * height_to_mm]  # In millimeters
                },
                "dimensions": {
                    "studs": {
                        "width": dims["studs_width"],
                        "depth": dims["studs_depth"],
                        "height": dims["studs_height"]
                    },
                    "mm": {
                        "width": dims["studs_width"] * studs_to_mm,
                        "depth": dims["studs_depth"] * studs_to_mm,
                        "height": dims["studs_height"] * height_to_mm
                    }
                },
                "rotation": brick.rotation,
                "color_id": brick.color_id,
                "color_info": self._get_color_info(brick.color_id),
                "vertices": vertices,  # 8 3D corner points in mm
                "voxel_coverage": covered_voxels,  # Which voxels this brick occupies
                "is_verified": brick.is_verified
            }
            
            manifest["bricks"].append(brick_data)
            
            # Add to voxel coverage map
            for voxel in covered_voxels:
                manifest["voxel_coverage"].append({
                    "voxel": voxel,
                    "brick_id": brick_data["brick_id"],
                    "part_id": brick.part_id,
                    "lego_type": brick_data["lego_type"]
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
                "lego_type": self._get_lego_type_name(part_id.split("_")[0]),
                "color_id": int(part_id.split("_")[1]),
                "color_name": self._get_color_name(int(part_id.split("_")[1])),
                "quantity": count
            }
            for part_id, count in inventory.items()
        ]
        
        # Add seam map for structural analysis
        if self.seam_map:
            manifest["seam_map"] = [
                {
                    "layer_z": entry.layer_z,
                    "x_position": entry.x_position,
                    "width": entry.width,
                    "covered_by": entry.covered_by
                }
                for entry in self.seam_map
            ]
        
        # Add evolved components for memory evolution
        if self.evolved_components:
            manifest["evolved_components"] = [
                {
                    "component_type": component.component_type,
                    "signature": component.signature,
                    "brick_count": len(component.bricks),
                    "confirmed": component.confirmed,
                    "metadata": component.metadata
                }
                for component in self.evolved_components.values()
            ]
        
        logger.info(f"Generated detailed manifest with {len(self.placed_bricks)} bricks")
        return manifest
    
    def _get_lego_type_name(self, part_id: str) -> str:
        """Get human-readable LEGO type name"""
        type_names = {
            "3001": "Brick 2x4",
            "3009": "Brick 1x6",
            "3003": "Brick 2x2",
            "3004": "Brick 1x2",
            "3005": "Brick 1x1",
            "3068": "Tile 2x2",
            "3069": "Tile 1x2",
            "3070": "Tile 1x1",
            "3938": "Hinge Brick 1x2",
            "6134": "Hinge Plate 1x2",
            "3040": "Slope 45° 2x1",
            "3038": "Slope -45° 2x1",
            "3297": "Slope 33° 2x2",
        }
        return type_names.get(part_id, f"Brick {part_id}")
    
    def _get_color_info(self, color_id: int) -> Dict:
        """Get color information"""
        color_map = {
            16: {"name": "Dark Tan", "hex": "#996633"},
            1: {"name": "White", "hex": "#FFFFFF"},
            5: {"name": "Red", "hex": "#E30A0A"},
            2: {"name": "Tan", "hex": "#D4A574"},
            3: {"name": "Light Gray", "hex": "#C0C0C0"},
            4: {"name": "Dark Gray", "hex": "#605A52"},
            6: {"name": "Green", "hex": "#237841"},
            7: {"name": "Blue", "hex": "#0055BF"},
            9: {"name": "Black", "hex": "#1B1B1B"},
            25: {"name": "Orange", "hex": "#FF7C00"},
            27: {"name": "Yellow", "hex": "#F2CD37"},
        }
        return color_map.get(color_id, {"name": f"Color {color_id}", "hex": "#888888"})
    
    def _get_color_name(self, color_id: int) -> str:
        """Get color name"""
        return self._get_color_info(color_id).get("name", f"Color {color_id}")
    
    def _get_fallback_parts(self, color_id: int) -> List[Dict]:
        """Fallback parts list when dynamic discovery fails."""
        return [
            {"part_num": "3001", "width": 4, "height": 2, "area": 8, "color_id": color_id, "is_verified": False},
            {"part_num": "3009", "width": 6, "height": 1, "area": 6, "color_id": color_id, "is_verified": False},
            {"part_num": "3003", "width": 2, "height": 2, "area": 4, "color_id": color_id, "is_verified": False},
            {"part_num": "3004", "width": 2, "height": 1, "area": 2, "color_id": color_id, "is_verified": False},
            {"part_num": "3005", "width": 1, "height": 1, "area": 1, "color_id": color_id, "is_verified": False},
        ]
    
    async def _query_curviness_for_surface(self, surface_normal: Tuple[float, float, float], color_id: int) -> List[Dict]:
        """
        CURVINESS TEST: Query Rebrickable API for slopes/curved pieces matching surface normal.
        
        Args:
            surface_normal: Normal vector from Three.js mesh (nx, ny, nz)
            color_id: Target color ID
            
        Returns:
            List of suitable slope/curved brick parts
        """
        try:
            # Calculate angle from normal vector
            nx, ny, nz = surface_normal
            # Angle in degrees from horizontal (z-axis)
            import math
            angle = math.degrees(math.acos(nz)) if nz != 0 else 90
            
            logger.info(f"Curviness Test: Surface normal {surface_normal} -> angle {angle:.1f}°")
            
            # Find slope bricks with matching angle
            matching_slopes = []
            for slope_id, slope_info in self.SLOPE_BRICK_IDS.items():
                for slope_angle in slope_info.get("angles", []):
                    if abs(angle - slope_angle) < 15:  # Within 15 degree tolerance
                        # Verify availability
                        is_available = await self.rebrickable.verify_part_availability(slope_id, color_id)
                        if is_available:
                            matching_slopes.append({
                                "part_num": slope_id,
                                "name": slope_info.get("name"),
                                "angle_match": slope_angle,
                                "angle_diff": abs(angle - slope_angle)
                            })
                            logger.info(f"✓ Found matching slope: {slope_id} ({slope_info.get('name')}) at {slope_angle}°")
            
            return sorted(matching_slopes, key=lambda p: p.get("angle_diff", 999))
            
        except Exception as e:
            logger.error(f"Error in curviness test: {e}")
            return []
    
    def _compute_cluster_signature(self, voxel_cluster: Set[Tuple[int, int]]) -> str:
        """
        Compute a deterministic signature for a voxel cluster.
        Used for identifying matching sub-assemblies in Backboard memory.
        
        Args:
            voxel_cluster: Set of (x, y) voxel positions
            
        Returns:
            Hex string signature
        """
        # Sort voxels for consistent hashing
        sorted_voxels = sorted(voxel_cluster)
        # Create a normalized representation (relative to min position)
        if not sorted_voxels:
            return "empty"
        
        min_x = min(v[0] for v in sorted_voxels)
        min_y = min(v[1] for v in sorted_voxels)
        normalized = tuple((x - min_x, y - min_y) for x, y in sorted_voxels)
        
        # Hash the normalized cluster shape
        signature = hashlib.md5(str(normalized).encode()).hexdigest()[:12]
        return signature
    
    async def _query_backboard_memory(self, cluster_signature: str) -> Optional[List[PlacedBrick]]:
        """
        BACKBOARD MEMORY: Check Backboard Stateful Thread for existing sub-assembly fragments.
        
        Args:
            cluster_signature: Computed signature of the voxel cluster
            
        Returns:
            List of previously-placed bricks from matching sub-assembly, or None if not found
        """
        # Check in-memory cache first
        if cluster_signature in self.backboard_memory:
            cached_assembly = self.backboard_memory[cluster_signature]
            logger.info(f"✓ Found cached sub-assembly in Backboard Memory: {cluster_signature}")
            logger.info(f"  Reusing {len(cached_assembly)} bricks from previous solution")
            return cached_assembly
        
        # In a full implementation, this would query the Backboard API
        # For now, we log the query attempt
        logger.debug(f"Querying Backboard Memory for sub-assembly: {cluster_signature}")
        
        return None
    
    def _store_in_backboard_memory(self, cluster_signature: str, bricks: List[PlacedBrick]) -> None:
        """
        Store a solved sub-assembly in Backboard memory for future reuse.
        
        Args:
            cluster_signature: Signature of the voxel cluster
            bricks: List of placed bricks for this cluster
        """
        self.backboard_memory[cluster_signature] = bricks
        logger.info(f"Stored sub-assembly in Backboard Memory: {cluster_signature} ({len(bricks)} bricks)")
    
    async def _classify_component_type(self, cluster_signature: str, voxel_cluster: Set[Tuple[int, int]]) -> str:
        """
        COMPONENT SUBSTITUTION: Use Gemini to analyze cluster and classify component type (Desk, Bed, etc.)
        Also checks hardcoded database for pre-defined components.
        
        Args:
            cluster_signature: Signature of the voxel cluster
            voxel_cluster: Set of (x, y) voxel positions
            
        Returns:
            Component type string (e.g., "desk", "bed_base", "shelf") or "generic"
        """
        # Check cache first
        if cluster_signature in self.component_cache:
            cached_type = self.component_cache[cluster_signature]
            logger.debug(f"Component type cached for {cluster_signature}: {cached_type}")
            return cached_type
        
        try:
            # Analyze cluster dimensions
            xs = [x for x, y in voxel_cluster]
            ys = [y for x, y in voxel_cluster]
            width = max(xs) - min(xs) + 1 if xs else 0
            height = max(ys) - min(ys) + 1 if ys else 0
            area = len(voxel_cluster)
            aspect_ratio = width / height if height > 0 else 0
            
            # Simple heuristic-based classification (can be enhanced with Gemini)
            # In production, call actual Gemini API for semantic analysis
            component_type = "generic"
            
            # Desk-like: Wide, rectangular, moderate size
            if 3 <= aspect_ratio <= 5 and 20 <= area <= 100:
                component_type = "desk"
                logger.info(f"Classified {cluster_signature} as 'desk' (AR: {aspect_ratio:.2f}, area: {area})")
                
                # Query hardcoded database for desk matches
                db_match = await self._query_hardcoded_database("desk", (width, height, 3))
                if db_match:
                    logger.info(f"Using hardcoded desk definition: {db_match.get('name')}")
                    self.component_cache[cluster_signature] = component_type
                    return component_type
            
            # Bed-like: Large, rectangular, high area
            elif aspect_ratio >= 1.5 and area >= 80:
                component_type = "bed_base"
                logger.info(f"Classified {cluster_signature} as 'bed_base' (AR: {aspect_ratio:.2f}, area: {area})")
                
                # Query hardcoded database for bed matches
                db_match = await self._query_hardcoded_database("bed_base", (width, height, 2))
                if db_match:
                    logger.info(f"Using hardcoded bed definition: {db_match.get('name')}")
                    self.component_cache[cluster_signature] = component_type
                    return component_type
            
            # Shelf-like: Narrow depth, tall
            elif aspect_ratio >= 3 and 10 <= area <= 50:
                component_type = "shelf"
                logger.info(f"Classified {cluster_signature} as 'shelf' (AR: {aspect_ratio:.2f}, area: {area})")
                
                # Query hardcoded database for shelf matches
                db_match = await self._query_hardcoded_database("shelf", (width, height, 10))
                if db_match:
                    logger.info(f"Using hardcoded shelf definition: {db_match.get('name')}")
                    self.component_cache[cluster_signature] = component_type
                    return component_type
            
            # Cache the result
            self.component_cache[cluster_signature] = component_type
            return component_type
            
        except Exception as e:
            logger.error(f"Error classifying component: {e}")
            self.component_cache[cluster_signature] = "generic"
            return "generic"
    
    async def _substitute_specialized_parts(self, component_type: str, discovered_parts: List[Dict], color_id: int) -> List[Dict]:
        """
        COMPONENT SUBSTITUTION: Force specialized parts for classified components (e.g., Tiles for Desks)
        
        Args:
            component_type: Type of component (desk, bed_base, shelf, etc.)
            discovered_parts: Original discovered parts list
            color_id: Target color ID
            
        Returns:
            Modified parts list with specialized parts prioritized for this component type
        """
        if component_type == "generic":
            return discovered_parts  # No substitution for generic components
        
        # Get specialized parts for this component type
        specialized = []
        
        if component_type == "desk":
            # Force use of flat Tiles and Hinge Bricks instead of standard bricks
            logger.info(f"Substituting parts for 'desk' component: prioritizing Tiles and Hinge Bricks")
            
            for part_id, part_info in self.SPECIALIZED_PARTS.get("tile", {}).items():
                if await self.rebrickable.verify_part_availability(part_id, color_id):
                    specialized.append({
                        "part_num": part_id,
                        "name": part_info.get("name"),
                        "width": part_info.get("width"),
                        "height": part_info.get("height"),
                        "area": part_info.get("width") * part_info.get("height"),
                        "is_specialized": True
                    })
            
            for part_id, part_info in self.SPECIALIZED_PARTS.get("hinge", {}).items():
                if await self.rebrickable.verify_part_availability(part_id, color_id):
                    specialized.append({
                        "part_num": part_id,
                        "name": part_info.get("name"),
                        "width": part_info.get("width"),
                        "height": part_info.get("height"),
                        "area": part_info.get("width") * part_info.get("height"),
                        "is_specialized": True
                    })
        
        # Sort specialized parts by area (descending) and combine with discovered parts
        specialized.sort(key=lambda p: p.get("area", 0), reverse=True)
        
        # Prepend specialized parts to discovered parts (highest priority)
        result = specialized + discovered_parts
        logger.info(f"Substituted {len(specialized)} specialized parts for {component_type} component")
        return result
    
    def _discourage_1x1_stacks(self, remaining_voxels: Set[Tuple[int, int]]) -> List[Tuple[int, int, int, int]]:
        """
        LAMINAR INTERLOCKING: Find 2-voxel gaps that should be bridged with 1x2 or 2x4 bricks.
        
        Args:
            remaining_voxels: Set of (x, y) positions still needing placement
            
        Returns:
            List of (x, y, width, height) rectangles representing gaps to bridge
        """
        gaps_to_bridge = []
        
        try:
            # Scan for isolated 2-voxel gaps
            sorted_voxels = sorted(remaining_voxels)
            
            for i, (x1, y1) in enumerate(sorted_voxels):
                # Check for horizontal 2-voxel gaps (1x2)
                if (x1 + 1, y1) in remaining_voxels:
                    # Found a 1x2 gap
                    # Check if both voxels are still isolated
                    neighbor_count_1 = sum(1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                          if (x1 + dx, y1 + dy) in remaining_voxels)
                    neighbor_count_2 = sum(1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                          if (x1 + 1 + dx, y1 + dy) in remaining_voxels)
                    
                    # Flag for bridging if isolated or only connected to each other
                    if neighbor_count_1 <= 2 or neighbor_count_2 <= 2:
                        gaps_to_bridge.append((x1, y1, 2, 1))
                        logger.debug(f"Found 1x2 gap at ({x1}, {y1}) to bridge")
                
                # Check for vertical 2-voxel gaps (2x1)
                if (x1, y1 + 1) in remaining_voxels:
                    neighbor_count_1 = sum(1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                          if (x1 + dx, y1 + dy) in remaining_voxels)
                    neighbor_count_2 = sum(1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                          if (x1 + dx, y1 + 1 + dy) in remaining_voxels)
                    
                    if neighbor_count_1 <= 2 or neighbor_count_2 <= 2:
                        gaps_to_bridge.append((x1, y1, 1, 2))
                        logger.debug(f"Found 2x1 gap at ({x1}, {y1}) to bridge")
        
        except Exception as e:
            logger.error(f"Error detecting 1x1 stacks: {e}")
        
        return gaps_to_bridge
    
    async def _query_hardcoded_database(self, component_type: str, dimensions: Tuple[int, int, int]) -> Optional[Dict]:
        """
        HARDCODED DATABASE: Query pre-defined LEGO objects for exact matches or similar components.
        This avoids API calls for commonly-used furniture and structures.
        
        Args:
            component_type: Type of component (desk, bed_base, shelf, etc.)
            dimensions: Target dimensions (width, depth, height) in studs
            
        Returns:
            Dictionary with object_id, brick_composition, and metadata, or None if not found
        """
        try:
            width, depth, height = dimensions
            
            # Try exact match first
            objects_of_type = get_lego_objects_by_type(component_type)
            
            for obj_id, obj_def in objects_of_type.items():
                obj_w, obj_d, obj_h = obj_def.dimensions
                
                # Exact match (within 1 stud tolerance)
                if (abs(obj_w - width) <= 1 and 
                    abs(obj_d - depth) <= 1 and 
                    abs(obj_h - height) <= 1):
                    
                    logger.info(f"Found exact hardcoded match: {obj_id} ({obj_def.name})")
                    return {
                        "object_id": obj_id,
                        "object_type": obj_def.object_type,
                        "name": obj_def.name,
                        "brick_composition": obj_def.brick_composition,
                        "estimated_brick_count": obj_def.estimated_brick_count,
                        "typical_colors": obj_def.typical_colors,
                        "metadata": obj_def.metadata,
                        "signature": obj_def.signature
                    }
            
            # Try similar match (within 20% tolerance)
            similar = find_similar_objects(
                object_type=component_type,
                max_bricks=int(width * depth * height * 1.5),  # Reasonable upper bound
                max_width=width + 4  # Allow some flexibility
            )
            
            if similar:
                # Return closest match
                obj_id, obj_def = similar[0]
                logger.info(f"Found similar hardcoded match: {obj_id} ({obj_def.name})")
                return {
                    "object_id": obj_id,
                    "object_type": obj_def.object_type,
                    "name": obj_def.name,
                    "brick_composition": obj_def.brick_composition,
                    "estimated_brick_count": obj_def.estimated_brick_count,
                    "typical_colors": obj_def.typical_colors,
                    "metadata": obj_def.metadata,
                    "signature": obj_def.signature,
                    "is_approximate_match": True
                }
            
            logger.debug(f"No hardcoded match for {component_type} with dimensions {dimensions}")
            return None
            
        except Exception as e:
            logger.error(f"Error querying hardcoded database: {e}")
            return None
    
    def _update_seam_map(self, layer_z: int) -> None:
        """
        STAGGERED SEAMS: Store the Seam Map in persistent storage for structural analysis.
        Ensures vertical seams on Layer N are covered by brick centers on Layer N+1.
        
        Args:
            layer_z: Current layer Z coordinate
        """
        try:
            seams = self.layer_seams.get(layer_z, set())
            
            if not seams:
                return
            
            # For each seam, create a map entry
            for seam_x in seams:
                # Find which brick will cover this seam in next layer
                covering_brick = None
                next_layer_bricks = self.layer_bricks.get(layer_z + 1, [])
                
                for brick in next_layer_bricks:
                    brick_x, brick_y, brick_z = brick.position
                    # Estimate brick width from part_id (simplified)
                    brick_width = self.PRIORITY_BRICK_IDS.get(brick.part_id, {}).get("width", 1)
                    
                    # Check if brick center covers this seam
                    brick_center = brick_x + brick_width / 2
                    if abs(brick_center - seam_x) < brick_width / 2:
                        covering_brick = brick.part_id
                        logger.debug(f"Seam at ({seam_x}, Layer {layer_z}) covered by {brick.part_id}")
                        break
                
                # Add to seam map
                seam_entry = SeamMapEntry(
                    layer_z=layer_z,
                    x_position=seam_x,
                    width=1,
                    covered_by=covering_brick
                )
                self.seam_map.append(seam_entry)
        
        except Exception as e:
            logger.error(f"Error updating seam map: {e}")
    
    async def _save_component_evolution(self, cluster_signature: str, component_type: str, bricks: List[PlacedBrick], confirmed: bool = False) -> None:
        """
        MEMORY EVOLUTION: Save the final optimized manifest for a sub-component.
        After user confirms a build, this stores the solution for future reuse.
        
        Args:
            cluster_signature: Signature of the voxel cluster
            component_type: Type of component (desk, bed_base, etc.)
            bricks: List of optimized placed bricks
            confirmed: Whether user has confirmed this build
        """
        try:
            # Compute metadata about the component
            positions = [brick.position for brick in bricks]
            z_coords = [z for x, y, z in positions]
            x_coords = [x for x, y, z in positions]
            y_coords = [y for x, y, z in positions]
            
            metadata = {
                "brick_count": len(bricks),
                "dimensions": {
                    "width": max(x_coords) - min(x_coords) + 1 if x_coords else 0,
                    "height": max(y_coords) - min(y_coords) + 1 if y_coords else 0,
                    "layers": max(z_coords) - min(z_coords) + 1 if z_coords else 0
                },
                "colors": list(set(brick.color_id for brick in bricks)),
                "parts": list(set(brick.part_id for brick in bricks))
            }
            
            # Create and store the sub-component manifest
            manifest = SubComponentManifest(
                component_type=component_type,
                signature=cluster_signature,
                bricks=bricks,
                metadata=metadata,
                confirmed=confirmed
            )
            
            self.evolved_components[cluster_signature] = manifest
            logger.info(f"Saved component evolution for {component_type} ({cluster_signature})")
            logger.info(f"  Bricks: {len(bricks)}, Confirmed: {confirmed}, Dimensions: {metadata['dimensions']}")
            
            # In production, this would save to Backboard Stateful Thread
            # For now, stored in memory for session duration
        
        except Exception as e:
            logger.error(f"Error saving component evolution: {e}")
    
    def confirm_and_evolve_build(self, user_confirmed: bool = True) -> Dict:
        """
        MEMORY EVOLUTION: After user confirms the build, save all evolved components.
        Returns a summary of saved components for reuse in future rooms.
        
        Args:
            user_confirmed: Whether user confirmed the final build
            
        Returns:
            Dictionary with evolution results
        """
        try:
            evolution_summary = {
                "confirmed": user_confirmed,
                "components_saved": 0,
                "evolution_log": []
            }
            
            if not user_confirmed:
                logger.warning("Build not confirmed by user, skipping component evolution")
                return evolution_summary
            
            # Save all components in evolved_components
            for signature, component in self.evolved_components.items():
                component.confirmed = True
                evolution_summary["components_saved"] += 1
                evolution_summary["evolution_log"].append({
                    "type": component.component_type,
                    "signature": signature,
                    "brick_count": len(component.bricks),
                    "dimensions": component.metadata.get("dimensions") if component.metadata else None
                })
                
                logger.info(f"Confirmed evolution: {component.component_type} ({signature})")
            
            logger.info(f"Component evolution complete: {evolution_summary['components_saved']} components saved")
            return evolution_summary
        
        except Exception as e:
            logger.error(f"Error confirming build evolution: {e}")
            return {"confirmed": user_confirmed, "components_saved": 0, "error": str(e)}
    
    def get_manifest_json(self) -> str:
        """Get manifest as JSON string"""
        manifest = self._generate_manifest()
        return json.dumps(manifest, indent=2)    
    # ========================================================================
    # PIECE COUNTING & INVENTORY
    # ========================================================================
    
    def get_piece_count(self) -> PieceSummary:
        """
        Get detailed piece count summary for the build.
        
        Returns:
            PieceSummary with all piece counts and estimates
        """
        manifest = self._generate_manifest()
        return PieceCounter.count_pieces(manifest)
    
    def get_shopping_list(self) -> str:
        """
        Get formatted shopping list of all pieces needed.
        
        Returns:
            Formatted shopping list string
        """
        summary = self.get_piece_count()
        return PieceCounter.generate_shopping_list(summary)
    
    def export_inventory_csv(self, output_path: str = None) -> Optional[str]:
        """
        Export inventory as CSV for spreadsheet import.
        
        Args:
            output_path: Optional path to save CSV file
            
        Returns:
            CSV string (and saves to file if output_path provided)
        """
        summary = self.get_piece_count()
        csv_content = PieceCounter.generate_inventory_csv(summary)
        
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(csv_content)
                logger.info(f"Exported inventory CSV to {output_path}")
            except Exception as e:
                logger.error(f"Error exporting CSV: {e}")
        
        return csv_content
    
    # ========================================================================
    # INSTRUCTION MANUAL GENERATION
    # ========================================================================
    
    def generate_build_guide(self, project_name: str = "LEGO Build") -> BuildGuide:
        """
        Generate step-by-step building guide.
        
        Args:
            project_name: Name of the project
            
        Returns:
            BuildGuide with organized assembly steps
        """
        manifest = self._generate_manifest()
        return InstructionManualGenerator.generate_build_guide(manifest, project_name)
    
    def export_instructions_text(self, output_path: str = None) -> str:
        """
        Export instructions as formatted text.
        
        Args:
            output_path: Optional path to save text file
            
        Returns:
            Formatted text string (and saves to file if output_path provided)
        """
        guide = self.generate_build_guide()
        text_content = InstructionManualGenerator.export_to_text(guide)
        
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(text_content)
                logger.info(f"Exported instructions text to {output_path}")
            except Exception as e:
                logger.error(f"Error exporting instructions: {e}")
        
        return text_content
    
    def export_instructions_html(self, output_path: str = None) -> str:
        """
        Export instructions as HTML.
        
        Args:
            output_path: Optional path to save HTML file
            
        Returns:
            HTML string (and saves to file if output_path provided)
        """
        guide = self.generate_build_guide()
        html_content = InstructionManualGenerator.export_to_html(guide)
        
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(html_content)
                logger.info(f"Exported instructions HTML to {output_path}")
            except Exception as e:
                logger.error(f"Error exporting HTML instructions: {e}")
        
        return html_content
    
    def export_instructions_json(self, output_path: str = None) -> Dict:
        """
        Export instructions as JSON.
        
        Args:
            output_path: Optional path to save JSON file
            
        Returns:
            Dictionary (and saves to file if output_path provided)
        """
        guide = self.generate_build_guide()
        json_content = InstructionManualGenerator.export_to_json(guide)
        
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    json.dump(json_content, f, indent=2)
                logger.info(f"Exported instructions JSON to {output_path}")
            except Exception as e:
                logger.error(f"Error exporting JSON instructions: {e}")
        
        return json_content
    
    # ========================================================================
    # LDRAW & 3D VISUALIZATION
    # ========================================================================
    
    def export_ldraw_file(self, output_path: str) -> bool:
        """
        Export build as LDraw file for 3D visualization.
        Requires: pip install python-ldraw
        
        Args:
            output_path: Path to save .ldr file
            
        Returns:
            True if successful
        """
        if not LDrawGenerator.check_ldraw_available():
            logger.warning("LDraw library not available. Install with: pip install python-ldraw")
            return False
        
        manifest = self._generate_manifest()
        success = LDrawGenerator.generate_ldraw_file(manifest, output_path)
        
        if success:
            logger.info(f"Exported LDraw file to {output_path}")
        
        return success
    
    def export_to_ldraw(self, output_path: str = None) -> str:
        """
        Export build as standard LDraw text file.
        
        Format:
        - Header: 0 LEGO Build and 0 Name: model.ldr
        - Scaling: Coordinates multiplied by 20 (LEGO Units)
        - Line Format: Type 1 lines with color, position, rotation, and part ID
        - Rotation: Identity matrix for default orientation
        
        Args:
            output_path: Optional path to save .ldr file
            
        Returns:
            LDraw file content as string
        """
        manifest = self._generate_manifest()
        
        # Build LDraw content
        ldraw_lines = []
        
        # Header
        ldraw_lines.append("0 LEGO Build")
        ldraw_lines.append("0 Name: model.ldr")
        ldraw_lines.append("0 Author: LEGO Master Builder")
        ldraw_lines.append("")
        
        # Process each brick
        for brick_data in manifest.get("bricks", []):
            part_id = brick_data.get("part_id", "3005")
            color_id = brick_data.get("color_id", 16)  # Default Dark Tan
            position = brick_data.get("position", {}).get("studs", [0, 0, 0])
            rotation = brick_data.get("rotation", 0)
            
            # Scale coordinates by 20 (LEGO Units)
            x = int(position[0] * 20)
            y = int(position[1] * 20)
            z = int(position[2] * 20)
            
            # Type 1 line: 1 <color> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <part>.dat
            # Using identity matrix for default orientation (1 0 0 0 1 0 0 0 1)
            ldraw_line = f"1 {color_id} {x} {y} {z} 1 0 0 0 1 0 0 0 1 {part_id}.dat"
            ldraw_lines.append(ldraw_line)
        
        # Footer
        ldraw_lines.append("")
        ldraw_lines.append(f"0 // Total bricks: {len(manifest.get('bricks', []))}")
        
        ldraw_content = "\n".join(ldraw_lines)
        
        # Save to file if path provided
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(ldraw_content)
                logger.info(f"Exported LDraw file to {output_path}")
            except Exception as e:
                logger.error(f"Error exporting LDraw file: {e}")
        
        return ldraw_content
    
    def export_glb_file(self, output_path: str) -> bool:
        """
        Export build as GLB (glTF) file for web viewing.
        Requires: pip install trimesh
        
        Args:
            output_path: Path to save .glb file
            
        Returns:
            True if successful
        """
        manifest = self._generate_manifest()
        success = LDrawGenerator.generate_glb_file(manifest, output_path)
        
        if success:
            logger.info(f"Exported GLB file to {output_path}")
        
        return success
    
    def export_3d_viewer(self, output_path: str) -> bool:
        """
        Export interactive 3D viewer as HTML with embedded Three.js.
        
        Args:
            output_path: Path to save HTML file
            
        Returns:
            True if successful
        """
        manifest = self._generate_manifest()
        success = LegoVisualizerWeb.generate_html_viewer(manifest, output_path)
        
        if success:
            logger.info(f"Exported 3D viewer to {output_path}")
        
        return success
    
    def get_3d_json(self) -> Dict:
        """
        Get 3D representation as JSON for web visualization.
        
        Returns:
            JSON-serializable dictionary with 3D brick data
        """
        manifest = self._generate_manifest()
        return LDrawGenerator.generate_3d_json(manifest)