"""
Three.js Scene to Voxel Converter

Converts Three.js 3D geometry into voxel grid representation.
Handles boxes, spheres, cylinders, and planes.
"""

import logging
from typing import List, Dict, Tuple, Optional
import math

logger = logging.getLogger(__name__)


class VoxelGrid:
    """Represents a 3D voxel grid"""
    
    def __init__(self, resolution: float = 0.1):
        """
        Initialize voxel grid.
        
        Args:
            resolution: Voxel size in meters (default 0.1m = 10cm)
        """
        self.resolution = resolution
        self.voxels: Dict[Tuple[int, int, int], str] = {}  # (x, y, z) -> hex_color
    
    def add_voxel(self, x: float, y: float, z: float, hex_color: str = "#888888"):
        """Add voxel at position"""
        grid_x = int(round(x / self.resolution))
        grid_y = int(round(y / self.resolution))
        grid_z = int(round(z / self.resolution))
        
        self.voxels[(grid_x, grid_y, grid_z)] = hex_color
    
    def add_box(self, x: float, y: float, z: float, 
                width: float, height: float, depth: float, 
                hex_color: str = "#888888"):
        """Add box to voxel grid"""
        # Box dimensions in voxels
        voxels_w = max(1, int(width / self.resolution / 2))
        voxels_h = max(1, int(height / self.resolution / 2))
        voxels_d = max(1, int(depth / self.resolution / 2))
        
        # Center position
        cx = int(round(x / self.resolution))
        cy = int(round(y / self.resolution))
        cz = int(round(z / self.resolution))
        
        # Fill box
        for i in range(-voxels_w, voxels_w + 1):
            for j in range(-voxels_h, voxels_h + 1):
                for k in range(-voxels_d, voxels_d + 1):
                    # Only fill outer shell for efficiency
                    if abs(i) == voxels_w or abs(j) == voxels_h or abs(k) == voxels_d:
                        self.voxels[(cx + i, cy + j, cz + k)] = hex_color
    
    def add_sphere(self, x: float, y: float, z: float, 
                   radius: float, hex_color: str = "#888888"):
        """Add sphere to voxel grid"""
        voxels_r = max(1, int(radius / self.resolution))
        cx = int(round(x / self.resolution))
        cy = int(round(y / self.resolution))
        cz = int(round(z / self.resolution))
        
        # Fill sphere
        for i in range(-voxels_r, voxels_r + 1):
            for j in range(-voxels_r, voxels_r + 1):
                for k in range(-voxels_r, voxels_r + 1):
                    dist = math.sqrt(i*i + j*j + k*k)
                    if dist <= voxels_r:
                        self.voxels[(cx + i, cy + j, cz + k)] = hex_color
    
    def add_cylinder(self, x: float, y: float, z: float, 
                     radius: float, height: float, 
                     hex_color: str = "#888888"):
        """Add cylinder to voxel grid"""
        voxels_r = max(1, int(radius / self.resolution))
        voxels_h = max(1, int(height / self.resolution / 2))
        
        cx = int(round(x / self.resolution))
        cy = int(round(y / self.resolution))
        cz = int(round(z / self.resolution))
        
        # Fill cylinder
        for i in range(-voxels_r, voxels_r + 1):
            for j in range(-voxels_h, voxels_h + 1):
                for k in range(-voxels_r, voxels_r + 1):
                    dist = math.sqrt(i*i + k*k)
                    if dist <= voxels_r:
                        self.voxels[(cx + i, cy + j, cz + k)] = hex_color
    
    def add_plane(self, x: float, y: float, z: float, 
                  width: float, height: float, 
                  hex_color: str = "#888888", thickness: float = 0.05):
        """Add plane to voxel grid"""
        voxels_w = max(1, int(width / self.resolution / 2))
        voxels_h = max(1, int(height / self.resolution / 2))
        voxels_t = max(1, int(thickness / self.resolution))
        
        cx = int(round(x / self.resolution))
        cy = int(round(y / self.resolution))
        cz = int(round(z / self.resolution))
        
        # Fill plane
        for i in range(-voxels_w, voxels_w + 1):
            for j in range(-voxels_h, voxels_h + 1):
                for k in range(-voxels_t, voxels_t + 1):
                    self.voxels[(cx + i, cy + j, cz + k)] = hex_color
    
    def to_voxel_list(self) -> List[Dict]:
        """Convert voxel grid to list of voxel objects"""
        voxel_list = []
        
        for (x, y, z), color in self.voxels.items():
            voxel_list.append({
                "x": x,
                "y": y,
                "z": z,
                "hex_color": color
            })
        
        logger.info(f"Generated {len(voxel_list)} voxels")
        return voxel_list


class ThreeJsVoxelizer:
    """Converts Three.js scene description to voxel data"""
    
    # Material color mapping from Three.js hex to readable hex
    MATERIAL_COLORS = {
        "0x555555": "#555555",  # floor gray
        "0xfdfdfd": "#fdfdfd",  # wall white
        "0xeebb99": "#eebb99",  # wood light
        "0x333333": "#333333",  # wood dark
        "0x111111": "#111111",  # metal black
        "0x334488": "#334488",  # fabric blue
        "0xeeeeee": "#eeeeee",  # plastic white
        "0xffcc00": "#ffcc00",  # pooh yellow
        "0xcc2222": "#cc2222",  # pooh red
        "0xff6600": "#ff6600",  # cone orange
        "0xccaa88": "#ccaa88",  # cork
        "0xffffff": "#ffffff",  # white
        "0x999999": "#999999",  # gray
        "0x000000": "#000000",  # black
        "0xcccccc": "#cccccc",  # light gray
    }
    
    def __init__(self, resolution: float = 0.15):
        """
        Initialize voxelizer.
        
        Args:
            resolution: Voxel size in meters (0.15m = 15cm for LEGO scale)
        """
        self.resolution = resolution
        self.grid = VoxelGrid(resolution)
    
    def parse_threejs_geometry(self, geometry_type: str, dimensions: Dict, 
                               position: Tuple[float, float, float],
                               color: str = "#888888") -> None:
        """
        Parse Three.js geometry and add to voxel grid.
        
        Args:
            geometry_type: Type of geometry (BoxGeometry, SphereGeometry, etc.)
            dimensions: Geometry dimensions
            position: Position (x, y, z)
            color: Hex color
        """
        x, y, z = position
        
        # Normalize color format
        if color.startswith("0x"):
            color = "#" + color[2:].upper()
        
        if geometry_type == "BoxGeometry":
            width = dimensions.get("width", 1)
            height = dimensions.get("height", 1)
            depth = dimensions.get("depth", 1)
            self.grid.add_box(x, y, z, width, height, depth, color)
        
        elif geometry_type == "SphereGeometry":
            radius = dimensions.get("radius", 0.5)
            self.grid.add_sphere(x, y, z, radius, color)
        
        elif geometry_type == "CylinderGeometry":
            radius = dimensions.get("radius", 0.5)
            height = dimensions.get("height", 1)
            self.grid.add_cylinder(x, y, z, radius, height, color)
        
        elif geometry_type == "PlaneGeometry":
            width = dimensions.get("width", 1)
            height = dimensions.get("height", 1)
            self.grid.add_plane(x, y, z, width, height, color)
        
        elif geometry_type == "ConeGeometry":
            # Treat cone as cylinder
            radius = dimensions.get("radius", 0.5)
            height = dimensions.get("height", 1)
            self.grid.add_cylinder(x, y, z, radius, height, color)
    
    def extract_from_json_scene(self, scene_data: Dict) -> List[Dict]:
        """
        Extract voxel data from JSON scene description.
        
        Expected format:
        {
            "objects": [
                {
                    "type": "BoxGeometry",
                    "position": [x, y, z],
                    "dimensions": {"width": 1, "height": 1, "depth": 1},
                    "color": "0x888888"
                },
                ...
            ]
        }
        """
        objects = scene_data.get("objects", [])
        
        for obj in objects:
            try:
                self.parse_threejs_geometry(
                    geometry_type=obj.get("type", "BoxGeometry"),
                    dimensions=obj.get("dimensions", {}),
                    position=tuple(obj.get("position", [0, 0, 0])),
                    color=obj.get("color", "#888888")
                )
            except Exception as e:
                logger.error(f"Error parsing object: {e}")
        
        return self.grid.to_voxel_list()
    
    def extract_dorm_room(self) -> List[Dict]:
        """
        Extract voxel data from sample dorm room scene.
        Hardcoded extraction of the sample Three.js dorm room.
        """
        
        # FLOOR
        self.grid.add_plane(0, 0, 0, 5, 5, "#555555", thickness=0.2)
        
        # WALLS
        self.grid.add_box(0, 1.5, -2.5, 5, 3, 0.1, "#fdfdfd")  # back wall
        self.grid.add_box(2.5, 1.5, 0, 0.1, 3, 5, "#fdfdfd")   # right wall
        self.grid.add_box(-2.5, 1.5, 0, 0.1, 3, 5, "#fdfdfd")  # left wall
        
        # SHELVES (Right Wall)
        for i in range(3):
            plank_y = 1.4 + i * 0.4
            self.grid.add_box(0, plank_y, 0, 1.2, 0.05, 0.25, "#eebb99")
            # Clutter on shelves
            for j in range(4):
                self.grid.add_box(
                    -0.4 + j * 0.3, 
                    plank_y + 0.1, 
                    0, 
                    0.08, 0.15, 0.08, 
                    "#aa5555"
                )
        
        # DESK AREA
        self.grid.add_box(1.5, 0.75, -2.1, 1.4, 0.05, 0.7, "#333333")  # desk top
        self.grid.add_box(1.5, 0.375, -2.1, 0.05, 0.75, 0.7, "#333333")  # legs
        self.grid.add_cylinder(1.9, 0.9, -2.0, 0.08, 0.25, "#eeeeee")  # pitcher
        self.grid.add_box(1.5, 0.4, -1.7, 0.5, 0.5, 0.5, "#334488")  # chair
        
        # DRESSER & DECORATIVE
        self.grid.add_box(-2.2, 0.45, -1.0, 1.2, 0.9, 0.5, "#eebb99")  # dresser
        # Pooh
        self.grid.add_sphere(-2.2, 1.15, -1.0, 0.25, "#ffcc00")  # body
        # Cone
        self.grid.add_cylinder(-1.8, 1.1, -1.0, 0.1, 0.4, "#ff6600")
        
        # WINDOW & RADIATOR
        self.grid.add_box(0, 2.0, -2.4, 1.5, 1.8, 0.1, "#334488")  # curtain
        self.grid.add_box(0, 0.3, -2.4, 1.5, 0.6, 0.15, "#eeeeee")  # radiator
        
        # BED (Corner Left)
        self.grid.add_box(-1.5, 0.25, 1.5, 2.0, 0.5, 1.2, "#eebb99")  # bed frame
        self.grid.add_box(-1.5, 0.35, 1.5, 1.9, 0.2, 1.1, "#eeeeee")  # mattress
        
        # COFFEE MAKER & FRIDGE
        self.grid.add_box(2.2, 0.4, -0.5, 0.6, 0.8, 0.6, "#111111")  # fridge
        self.grid.add_cylinder(2.2, 0.92, -0.5, 0.1, 0.25, "#999999")  # coffee maker
        
        return self.grid.to_voxel_list()


def convert_threejs_to_voxels(scene_description: Dict, resolution: float = 0.15) -> List[Dict]:
    """
    Main conversion function.
    
    Args:
        scene_description: Three.js scene as JSON
        resolution: Voxel resolution in meters
        
    Returns:
        List of voxel dictionaries ready for LEGO processing
    """
    voxelizer = ThreeJsVoxelizer(resolution=resolution)
    return voxelizer.extract_from_json_scene(scene_description)


def get_sample_dorm_room_voxels(resolution: float = 0.15) -> List[Dict]:
    """Get voxel data for sample dorm room"""
    voxelizer = ThreeJsVoxelizer(resolution=resolution)
    return voxelizer.extract_dorm_room()
