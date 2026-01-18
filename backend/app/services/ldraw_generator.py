"""
LDraw Integration Service
Generates LDraw files and 3D LEGO-like visualizations from manifests.
Uses the python-ldraw library to create authentic LEGO brick models.
"""

import logging
from typing import Dict, List, Tuple, Optional
import json
import os

logger = logging.getLogger(__name__)

# Note: This requires: pip install python-ldraw (or: pip install ldraw)
try:
    import ldraw
    LDRAW_AVAILABLE = True
except ImportError:
    LDRAW_AVAILABLE = False
    logger.warning("python-ldraw not installed. Install with: pip install python-ldraw")


# LDraw Part ID mapping from LEGO part IDs
LDRAW_PART_MAP = {
    # Standard bricks
    "3001": "3001.dat",      # Brick 2x4
    "3002": "3002.dat",      # Brick 2x3
    "3003": "3003.dat",      # Brick 2x2
    "3004": "3004.dat",      # Brick 1x2
    "3005": "3005.dat",      # Brick 1x1
    "3009": "3009.dat",      # Brick 1x6
    
    # Slopes
    "3040": "3040.dat",      # Slope 45° 2x1
    "3038": "3038.dat",      # Slope 45° Inverted
    "3297": "3297.dat",      # Slope 33° 2x2
    
    # Tiles
    "3068": "3068.dat",      # Tile 2x2
    "3069": "3069.dat",      # Tile 1x2
    "3070": "3070.dat",      # Tile 1x1
    
    # Hinges
    "3938": "3938.dat",      # Hinge Brick
    "6134": "6134.dat",      # Hinge Plate
}

# LDraw color codes (LEGO color ID to LDraw code)
LDRAW_COLOR_MAP = {
    1: 16,      # White
    2: 18,      # Tan
    3: 71,      # Light Gray
    4: 72,      # Dark Gray
    5: 4,       # Red
    6: 320,     # Dark Red
    7: 25,      # Brown
    8: 336,     # Dark Brown
    9: 14,      # Yellow
    10: 78,     # Light Yellow
    11: 2,      # Green
    12: 288,    # Dark Green
    13: 1,      # Blue
    14: 278,    # Dark Blue
    15: 0,      # Black
    16: 13,     # Orange
    17: 77,     # Light Blue
    18: 9,      # Purple
    19: 5,      # Pink
    20: 71,     # Beige
}

# LEGO stud size: 8mm = 1 unit in LDraw
# Standard brick height: 9.6mm per layer


class LDrawGenerator:
    """
    Generates LDraw files from LEGO manifests for 3D visualization.
    """
    
    @staticmethod
    def check_ldraw_available() -> bool:
        """Check if LDraw library is available"""
        return LDRAW_AVAILABLE
    
    @staticmethod
    def generate_ldraw_file(manifest: Dict, output_path: str, use_hardcoded: bool = True) -> bool:
        """
        Generate LDraw file from manifest.
        
        Args:
            manifest: The build manifest with bricks
            output_path: Path to save .ldr file
            use_hardcoded: Whether to reference hardcoded database objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not LDRAW_AVAILABLE:
                logger.error("LDraw library not available. Install with: pip install python-ldraw")
                return False
            
            lines = []
            
            # LDraw file header
            lines.append("1 16 0 0 0 1 0 0 0 1 0 0 0 1 model.ldr")
            
            # Add bricks
            for brick in manifest.get("bricks", []):
                ldraw_line = LDrawGenerator._brick_to_ldraw(brick)
                if ldraw_line:
                    lines.append(ldraw_line)
            
            # Write file
            with open(output_path, 'w') as f:
                f.write("\n".join(lines))
            
            logger.info(f"Generated LDraw file: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error generating LDraw file: {e}")
            return False
    
    @staticmethod
    def _brick_to_ldraw(brick: Dict) -> Optional[str]:
        """
        Convert a brick to LDraw format.
        
        Format: 1 <color> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <part.dat>
        
        Args:
            brick: Brick dictionary from manifest
            
        Returns:
            LDraw line string or None if invalid
        """
        try:
            part_id = brick.get("part_id")
            position = brick.get("position", [0, 0, 0])
            rotation = brick.get("rotation", 0)
            color_id = brick.get("color_id", 16)
            
            # Get LDraw part
            ldraw_part = LDRAW_PART_MAP.get(part_id)
            if not ldraw_part:
                logger.warning(f"Unknown part ID: {part_id}")
                return None
            
            # Get LDraw color
            ldraw_color = LDRAW_COLOR_MAP.get(color_id, 16)
            
            # Convert position (LDraw uses different coordinate system)
            x = position[0] * 20  # 20 LDraw units per stud
            y = position[2] * 24  # 24 LDraw units per layer (9.6mm = ~24 units)
            z = -position[1] * 20  # Inverted for LDraw coordinate system
            
            # Rotation matrix (simplified for 90° rotations)
            rotation_matrix = LDrawGenerator._get_rotation_matrix(rotation)
            
            # Build LDraw line
            # Format: 1 <color> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <part>
            ldraw_line = f"1 {ldraw_color} {x} {y} {z} {rotation_matrix} {ldraw_part}"
            
            return ldraw_line
        
        except Exception as e:
            logger.error(f"Error converting brick to LDraw: {e}")
            return None
    
    @staticmethod
    def _get_rotation_matrix(rotation_degrees: int) -> str:
        """
        Get LDraw rotation matrix for given rotation in degrees.
        
        Args:
            rotation_degrees: Rotation in degrees (0, 90, 180, 270)
            
        Returns:
            Rotation matrix as space-separated string
        """
        # Identity matrix
        if rotation_degrees == 0:
            return "1 0 0 0 1 0 0 0 1"
        # 90° clockwise
        elif rotation_degrees == 90:
            return "0 0 1 0 1 0 -1 0 0"
        # 180°
        elif rotation_degrees == 180:
            return "-1 0 0 0 1 0 0 0 -1"
        # 270° clockwise (90° counter-clockwise)
        elif rotation_degrees == 270:
            return "0 0 -1 0 1 0 1 0 0"
        else:
            return "1 0 0 0 1 0 0 0 1"
    
    @staticmethod
    def generate_mtl_file(output_path: str) -> bool:
        """
        Generate MTL (material) file for better 3D rendering.
        
        Args:
            output_path: Path to save .mtl file
            
        Returns:
            True if successful
        """
        try:
            lines = []
            lines.append("# LEGO Material Library")
            lines.append("")
            
            # Add material definitions for common colors
            materials = {
                "white": {"Ka": "1.0 1.0 1.0", "Kd": "1.0 1.0 1.0"},
                "red": {"Ka": "0.8 0.1 0.1", "Kd": "0.8 0.1 0.1"},
                "blue": {"Ka": "0.1 0.1 0.8", "Kd": "0.1 0.1 0.8"},
                "yellow": {"Ka": "1.0 1.0 0.0", "Kd": "1.0 1.0 0.0"},
                "green": {"Ka": "0.1 0.8 0.1", "Kd": "0.1 0.8 0.1"},
                "black": {"Ka": "0.1 0.1 0.1", "Kd": "0.1 0.1 0.1"},
            }
            
            for color, props in materials.items():
                lines.append(f"newmtl {color}")
                lines.append(f"  Ka {props['Ka']}")
                lines.append(f"  Kd {props['Kd']}")
                lines.append(f"  Ks 0.5 0.5 0.5")
                lines.append(f"  Ns 64")
                lines.append("")
            
            with open(output_path, 'w') as f:
                f.write("\n".join(lines))
            
            return True
        
        except Exception as e:
            logger.error(f"Error generating MTL file: {e}")
            return False
    
    @staticmethod
    def generate_glb_file(manifest: Dict, output_path: str) -> bool:
        """
        Generate GLB (glTF binary) file for web 3D viewing.
        
        Args:
            manifest: The build manifest
            output_path: Path to save .glb file
            
        Returns:
            True if successful
        """
        try:
            # This requires: pip install trimesh
            import trimesh
            
            logger.info("Generating GLB file with trimesh...")
            
            # Create scene
            scene = trimesh.Scene()
            
            # Add bricks as boxes (simplified representation)
            for brick in manifest.get("bricks", []):
                position = brick.get("position", [0, 0, 0])
                color_id = brick.get("color_id", 16)
                
                # Create box geometry (simplified - all bricks as 8mm units)
                box = trimesh.primitives.Box(extents=[8, 8, 8])
                
                # Set position
                box.apply_translation([position[0] * 8, position[1] * 8, position[2] * 9.6])
                
                # Set color based on LEGO color
                color = LDrawGenerator._get_color_rgb(color_id)
                box.visual.vertex_colors = color
                
                scene.add_geometry(box)
            
            # Export
            scene.export(output_path)
            logger.info(f"Generated GLB file: {output_path}")
            return True
        
        except ImportError:
            logger.error("trimesh not installed. Install with: pip install trimesh")
            return False
        except Exception as e:
            logger.error(f"Error generating GLB file: {e}")
            return False
    
    @staticmethod
    def _get_color_rgb(color_id: int) -> Tuple[int, int, int]:
        """
        Get RGB color for LEGO color ID.
        
        Args:
            color_id: LEGO color ID
            
        Returns:
            RGB tuple (0-255)
        """
        color_map = {
            1: (255, 255, 255),   # White
            2: (210, 180, 140),   # Tan
            3: (211, 211, 211),   # Light Gray
            4: (128, 128, 128),   # Dark Gray
            5: (255, 0, 0),       # Red
            6: (139, 0, 0),       # Dark Red
            7: (139, 69, 19),     # Brown
            8: (90, 40, 20),      # Dark Brown
            9: (255, 255, 0),     # Yellow
            10: (255, 255, 200),  # Light Yellow
            11: (0, 128, 0),      # Green
            12: (0, 100, 0),      # Dark Green
            13: (0, 0, 255),      # Blue
            14: (0, 0, 139),      # Dark Blue
            15: (0, 0, 0),        # Black
            16: (255, 165, 0),    # Orange
            17: (173, 216, 230),  # Light Blue
            18: (128, 0, 128),    # Purple
            19: (255, 192, 203),  # Pink
            20: (245, 245, 220),  # Beige
        }
        return color_map.get(color_id, (200, 200, 200))
    
    @staticmethod
    def generate_3d_json(manifest: Dict) -> Dict:
        """
        Generate JSON representation for web 3D visualization.
        
        Args:
            manifest: The build manifest
            
        Returns:
            Dictionary with 3D data
        """
        bricks_3d = []
        
        for brick in manifest.get("bricks", []):
            position = brick.get("position", [0, 0, 0])
            part_id = brick.get("part_id")
            color_id = brick.get("color_id", 16)
            rotation = brick.get("rotation", 0)
            
            brick_3d = {
                "part_id": part_id,
                "position": position,
                "rotation": rotation,
                "color_id": color_id,
                "color_rgb": LDrawGenerator._get_color_rgb(color_id),
                "size": LDrawGenerator._get_brick_size(part_id)
            }
            bricks_3d.append(brick_3d)
        
        return {
            "format": "LEGO 3D JSON",
            "version": "1.0",
            "total_bricks": len(bricks_3d),
            "bricks": bricks_3d
        }
    
    @staticmethod
    def _get_brick_size(part_id: str) -> Dict[str, float]:
        """
        Get brick dimensions in millimeters.
        
        Args:
            part_id: LEGO part ID
            
        Returns:
            Dictionary with width, depth, height in mm
        """
        sizes = {
            "3001": {"width": 32, "depth": 16, "height": 9.6},  # 2x4
            "3002": {"width": 24, "depth": 16, "height": 9.6},  # 2x3
            "3003": {"width": 16, "depth": 16, "height": 9.6},  # 2x2
            "3004": {"width": 16, "depth": 8, "height": 9.6},   # 1x2
            "3005": {"width": 8, "depth": 8, "height": 9.6},    # 1x1
            "3009": {"width": 48, "depth": 8, "height": 9.6},   # 1x6
            "3068": {"width": 16, "depth": 16, "height": 3.2},  # Tile 2x2
            "3069": {"width": 16, "depth": 8, "height": 3.2},   # Tile 1x2
            "3070": {"width": 8, "depth": 8, "height": 3.2},    # Tile 1x1
        }
        return sizes.get(part_id, {"width": 8, "depth": 8, "height": 9.6})


class LegoVisualizerWeb:
    """
    Web-based LEGO visualizer using Three.js compatible data.
    """
    
    @staticmethod
    def generate_html_viewer(manifest: Dict, output_path: str) -> bool:
        """
        Generate HTML file with embedded Three.js viewer.
        
        Args:
            manifest: The build manifest
            output_path: Path to save HTML file
            
        Returns:
            True if successful
        """
        try:
            # Generate 3D JSON data
            data_3d = LDrawGenerator.generate_3d_json(manifest)
            
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>LEGO Build 3D Viewer</title>
    <style>
        body { margin: 0; overflow: hidden; font-family: Arial; }
        #canvas { display: block; }
        #info {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 15px;
            border-radius: 5px;
            font-size: 12px;
            max-width: 300px;
            z-index: 100;
        }
        #info h3 { margin: 0 0 10px 0; }
        #info p { margin: 5px 0; }
    </style>
</head>
<body>
    <div id="info">
        <h3>LEGO Build Viewer</h3>
        <p>Total Bricks: """ + str(data_3d['total_bricks']) + """</p>
        <p>Drag to rotate | Scroll to zoom</p>
    </div>
    <canvas id="canvas"></canvas>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        const data = """ + json.dumps(data_3d) + """;
        
        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf0f0f0);
        
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 0, 100);
        
        const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas'), antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        
        // Lighting
        const light = new THREE.DirectionalLight(0xffffff, 1);
        light.position.set(100, 100, 100);
        light.castShadow = true;
        scene.add(light);
        
        scene.add(new THREE.AmbientLight(0x808080));
        
        // Add bricks
        data.bricks.forEach(brick => {
            const size = brick.size;
            const geometry = new THREE.BoxGeometry(size.width, size.height, size.depth);
            const material = new THREE.MeshPhongMaterial({
                color: new THREE.Color(...brick.color_rgb.map(c => c/255))
            });
            const mesh = new THREE.Mesh(geometry, material);
            
            mesh.position.set(brick.position[0] * 8, brick.position[2] * 9.6, brick.position[1] * 8);
            mesh.rotation.z = (brick.rotation * Math.PI / 180);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            
            scene.add(mesh);
        });
        
        // Mouse controls
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };
        
        document.addEventListener('mousedown', (e) => isDragging = true);
        document.addEventListener('mouseup', (e) => isDragging = false);
        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const deltaX = e.clientX - previousMousePosition.x;
                const deltaY = e.clientY - previousMousePosition.y;
                
                scene.rotation.y += deltaX * 0.01;
                scene.rotation.x += deltaY * 0.01;
            }
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        // Zoom with scroll
        document.addEventListener('wheel', (e) => {
            e.preventDefault();
            camera.position.z += e.deltaY * 0.1;
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
        
        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }
        animate();
    </script>
</body>
</html>
            """
            
            with open(output_path, 'w') as f:
                f.write(html)
            
            logger.info(f"Generated HTML viewer: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error generating HTML viewer: {e}")
            return False
