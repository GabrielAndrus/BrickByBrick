"""
Hardcoded LEGO Objects Database
Pre-defined common LEGO furniture, structures, and components for quick Backboard reference.
This avoids API calls for frequently-used objects and speeds up component matching.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class LegoObjectDefinition:
    """Definition of a pre-built LEGO object"""
    object_id: str  # Unique identifier (e.g., "desk_small_oak")
    object_type: str  # Category: "desk", "bed", "shelf", "chair", "table", "decorative"
    name: str  # Human-readable name
    signature: str  # Cluster signature hash for matching
    dimensions: Tuple[int, int, int]  # (width, depth, height) in studs
    brick_composition: Dict[str, int]  # part_id -> quantity
    estimated_brick_count: int  # Total brick count
    typical_colors: List[str]  # Hex colors commonly used
    metadata: Dict  # Additional info (material, style, tags)


# ============================================================================
# COMMON LEGO FURNITURE DATABASE
# ============================================================================

LEGO_OBJECTS_DATABASE = {
    # ========================================================================
    # DESKS (Work Surfaces)
    # ========================================================================
    "desk_small_oak": LegoObjectDefinition(
        object_id="desk_small_oak",
        object_type="desk",
        name="Small Desk (Oak)",
        signature="desk_small_oak_v1",
        dimensions=(12, 8, 3),  # 12w x 8d x 3h studs
        brick_composition={
            "3001": 8,    # 2x4 bricks (frame)
            "3002": 4,    # 2x3 bricks
            "3003": 12,   # 2x2 bricks (corners/support)
            "3068": 24,   # 2x2 tiles (desktop surface)
            "3069": 12,   # 1x2 tiles (edge trim)
        },
        estimated_brick_count=60,
        typical_colors=["#8B4513", "#D2B48C", "#A0522D"],  # Oak brown shades
        metadata={
            "style": "modern",
            "material": "simulated wood",
            "area": 96,
            "aspect_ratio": 1.5,
            "tags": ["furniture", "workspace", "office"]
        }
    ),
    
    "desk_medium_walnut": LegoObjectDefinition(
        object_id="desk_medium_walnut",
        object_type="desk",
        name="Medium Desk (Walnut)",
        signature="desk_medium_walnut_v1",
        dimensions=(16, 10, 3),  # 16w x 10d x 3h studs
        brick_composition={
            "3001": 12,   # 2x4 bricks
            "3009": 8,    # 1x6 bricks
            "3003": 16,   # 2x2 bricks
            "3068": 40,   # 2x2 tiles (large desktop)
            "3069": 20,   # 1x2 tiles
            "3070": 8,    # 1x1 tiles (corners)
        },
        estimated_brick_count=104,
        typical_colors=["#5C4033", "#8B6F47", "#6B4423"],  # Walnut brown shades
        metadata={
            "style": "traditional",
            "material": "simulated wood",
            "area": 160,
            "aspect_ratio": 1.6,
            "tags": ["furniture", "workspace", "office", "large"]
        }
    ),
    
    "desk_executive_black": LegoObjectDefinition(
        object_id="desk_executive_black",
        object_type="desk",
        name="Executive Desk (Black)",
        signature="desk_executive_black_v1",
        dimensions=(20, 12, 4),  # 20w x 12d x 4h studs
        brick_composition={
            "3001": 16,   # 2x4 bricks (main frame)
            "3009": 12,   # 1x6 bricks
            "3002": 8,    # 2x3 bricks
            "3003": 20,   # 2x2 bricks (support structure)
            "3068": 60,   # 2x2 tiles (desktop - premium)
            "3069": 30,   # 1x2 tiles
            "3070": 12,   # 1x1 tiles
        },
        estimated_brick_count=158,
        typical_colors=["#000000", "#1C1C1C", "#2F4F4F"],  # Black/dark tones
        metadata={
            "style": "contemporary",
            "material": "simulated composite",
            "area": 240,
            "aspect_ratio": 1.67,
            "tags": ["furniture", "workspace", "executive", "premium", "large"]
        }
    ),

    # ========================================================================
    # BEDS (Sleep Furniture)
    # ========================================================================
    "bed_twin_frame": LegoObjectDefinition(
        object_id="bed_twin_frame",
        object_type="bed_base",
        name="Twin Bed Frame",
        signature="bed_twin_frame_v1",
        dimensions=(12, 16, 2),  # 12w x 16d x 2h studs (mattress-sized)
        brick_composition={
            "3001": 20,   # 2x4 bricks (perimeter frame)
            "3009": 12,   # 1x6 bricks
            "3003": 24,   # 2x2 bricks (corner posts)
            "3004": 16,   # 1x2 bricks
            "3005": 8,    # 1x1 bricks (detail)
        },
        estimated_brick_count=80,
        typical_colors=["#8B4513", "#CD853F", "#D2B48C"],  # Wood tones
        metadata={
            "style": "platform",
            "material": "simulated wood",
            "area": 192,
            "aspect_ratio": 0.75,
            "tags": ["furniture", "sleep", "bed", "platform"]
        }
    ),

    "bed_queen_frame": LegoObjectDefinition(
        object_id="bed_queen_frame",
        object_type="bed_base",
        name="Queen Bed Frame",
        signature="bed_queen_frame_v1",
        dimensions=(16, 20, 2),  # 16w x 20d x 2h studs
        brick_composition={
            "3001": 32,   # 2x4 bricks (main frame)
            "3009": 16,   # 1x6 bricks
            "3002": 16,   # 2x3 bricks
            "3003": 32,   # 2x2 bricks (reinforcement)
            "3004": 20,   # 1x2 bricks
        },
        estimated_brick_count=116,
        typical_colors=["#8B4513", "#A0522D", "#CD853F"],  # Warm wood tones
        metadata={
            "style": "platform",
            "material": "simulated wood",
            "area": 320,
            "aspect_ratio": 0.8,
            "tags": ["furniture", "sleep", "bed", "platform", "large"]
        }
    ),

    # ========================================================================
    # SHELVES (Storage & Display)
    # ========================================================================
    "shelf_tall_4tier": LegoObjectDefinition(
        object_id="shelf_tall_4tier",
        object_type="shelf",
        name="Tall 4-Tier Shelf",
        signature="shelf_tall_4tier_v1",
        dimensions=(10, 8, 14),  # 10w x 8d x 14h studs (tall)
        brick_composition={
            "3001": 24,   # 2x4 bricks (vertical supports)
            "3009": 12,   # 1x6 bricks
            "3003": 16,   # 2x2 bricks
            "3069": 40,   # 1x2 tiles (shelf surfaces)
            "3068": 16,   # 2x2 tiles (corners)
        },
        estimated_brick_count=108,
        typical_colors=["#FFFFFF", "#D3D3D3", "#A9A9A9"],  # Light neutrals
        metadata={
            "style": "modern",
            "material": "simulated composite",
            "area": 80,
            "aspect_ratio": 1.25,
            "tier_count": 4,
            "tags": ["furniture", "storage", "display", "shelving", "tall"]
        }
    ),

    "shelf_wide_3tier": LegoObjectDefinition(
        object_id="shelf_wide_3tier",
        object_type="shelf",
        name="Wide 3-Tier Shelf",
        signature="shelf_wide_3tier_v1",
        dimensions=(16, 8, 10),  # 16w x 8d x 10h studs
        brick_composition={
            "3001": 28,   # 2x4 bricks
            "3009": 16,   # 1x6 bricks
            "3069": 48,   # 1x2 tiles (wide surfaces)
            "3003": 20,   # 2x2 bricks
        },
        estimated_brick_count=112,
        typical_colors=["#8B4513", "#CD853F", "#D2B48C"],  # Oak wood
        metadata={
            "style": "traditional",
            "material": "simulated wood",
            "area": 128,
            "aspect_ratio": 2.0,
            "tier_count": 3,
            "tags": ["furniture", "storage", "display", "shelving", "wide"]
        }
    ),

    # ========================================================================
    # CHAIRS
    # ========================================================================
    "chair_office_black": LegoObjectDefinition(
        object_id="chair_office_black",
        object_type="chair",
        name="Office Chair (Black)",
        signature="chair_office_black_v1",
        dimensions=(4, 4, 7),  # 4w x 4d x 7h studs
        brick_composition={
            "3003": 8,    # 2x2 bricks (seat)
            "3001": 4,    # 2x4 bricks (back support)
            "3004": 12,   # 1x2 bricks (legs/armrests)
            "3005": 6,    # 1x1 bricks (details)
            "3938": 2,    # Hinges (swivel)
        },
        estimated_brick_count=32,
        typical_colors=["#000000", "#1C1C1C", "#A9A9A9"],  # Black/gray
        metadata={
            "style": "modern",
            "material": "simulated plastic/leather",
            "area": 16,
            "aspect_ratio": 1.0,
            "tags": ["furniture", "seating", "office", "compact"]
        }
    ),

    # ========================================================================
    # TABLES (Dining/Coffee)
    # ========================================================================
    "table_dining_oak": LegoObjectDefinition(
        object_id="table_dining_oak",
        object_type="table",
        name="Dining Table (Oak)",
        signature="table_dining_oak_v1",
        dimensions=(16, 10, 3),  # 16w x 10d x 3h studs
        brick_composition={
            "3001": 16,   # 2x4 bricks (frame)
            "3009": 12,   # 1x6 bricks
            "3003": 16,   # 2x2 bricks
            "3068": 40,   # 2x2 tiles (table surface)
            "3069": 24,   # 1x2 tiles (perimeter)
        },
        estimated_brick_count=108,
        typical_colors=["#8B4513", "#A0522D", "#CD853F"],  # Oak tones
        metadata={
            "style": "traditional",
            "material": "simulated wood",
            "area": 160,
            "aspect_ratio": 1.6,
            "tags": ["furniture", "dining", "table", "large"]
        }
    ),

    "table_coffee_minimal": LegoObjectDefinition(
        object_id="table_coffee_minimal",
        object_type="table",
        name="Minimal Coffee Table",
        signature="table_coffee_minimal_v1",
        dimensions=(10, 6, 2),  # 10w x 6d x 2h studs
        brick_composition={
            "3001": 6,    # 2x4 bricks
            "3003": 6,    # 2x2 bricks
            "3069": 20,   # 1x2 tiles (surface)
            "3005": 4,    # 1x1 bricks (feet)
        },
        estimated_brick_count=36,
        typical_colors=["#FFFFFF", "#D3D3D3", "#696969"],  # Neutral
        metadata={
            "style": "minimalist",
            "material": "simulated composite",
            "area": 60,
            "aspect_ratio": 1.67,
            "tags": ["furniture", "table", "coffee", "minimal", "compact"]
        }
    ),

    # ========================================================================
    # DECORATIVE ELEMENTS
    # ========================================================================
    "plant_tall_potted": LegoObjectDefinition(
        object_id="plant_tall_potted",
        object_type="decorative",
        name="Tall Potted Plant",
        signature="plant_tall_potted_v1",
        dimensions=(2, 2, 8),  # 2w x 2d x 8h studs
        brick_composition={
            "3003": 4,    # 2x2 bricks (pot base)
            "3004": 8,    # 1x2 bricks (stem)
            "3005": 12,   # 1x1 bricks (leaves/foliage)
        },
        estimated_brick_count=24,
        typical_colors=["#8B4513", "#228B22", "#32CD32"],  # Terra/green
        metadata={
            "style": "natural",
            "material": "simulated ceramic/plant",
            "area": 4,
            "aspect_ratio": 1.0,
            "tags": ["decorative", "plant", "accent", "compact"]
        }
    ),

    "lamp_desk_modern": LegoObjectDefinition(
        object_id="lamp_desk_modern",
        object_type="decorative",
        name="Modern Desk Lamp",
        signature="lamp_desk_modern_v1",
        dimensions=(2, 2, 6),  # 2w x 2d x 6h studs
        brick_composition={
            "3003": 2,    # 2x2 bricks (base)
            "3001": 1,    # 2x4 bricks (arm joint)
            "3004": 4,    # 1x2 bricks (arm)
            "3005": 2,    # 1x1 bricks (shade)
        },
        estimated_brick_count=9,
        typical_colors=["#000000", "#FFFFFF", "#FFD700"],  # Black/white/gold
        metadata={
            "style": "contemporary",
            "material": "simulated metal/plastic",
            "area": 4,
            "aspect_ratio": 1.0,
            "tags": ["decorative", "lighting", "desk", "accent"]
        }
    ),

    # ========================================================================
    # STORAGE & ORGANIZATION
    # ========================================================================
    "dresser_bedroom_oak": LegoObjectDefinition(
        object_id="dresser_bedroom_oak",
        object_type="furniture",
        name="Bedroom Dresser (Oak)",
        signature="dresser_bedroom_oak_v1",
        dimensions=(12, 6, 7),  # 12w x 6d x 7h studs
        brick_composition={
            "3001": 12,   # 2x4 bricks
            "3003": 16,   # 2x2 bricks
            "3069": 24,   # 1x2 tiles (drawer fronts/surface)
            "3004": 8,    # 1x2 bricks
        },
        estimated_brick_count=60,
        typical_colors=["#8B4513", "#CD853F", "#D2B48C"],  # Oak
        metadata={
            "style": "traditional",
            "material": "simulated wood",
            "area": 72,
            "aspect_ratio": 2.0,
            "tags": ["furniture", "storage", "bedroom", "dresser"]
        }
    ),

    "bookcase_corner": LegoObjectDefinition(
        object_id="bookcase_corner",
        object_type="furniture",
        name="Corner Bookcase",
        signature="bookcase_corner_v1",
        dimensions=(8, 8, 12),  # 8w x 8d x 12h studs
        brick_composition={
            "3001": 20,   # 2x4 bricks
            "3003": 12,   # 2x2 bricks
            "3069": 32,   # 1x2 tiles (shelves)
            "3004": 12,   # 1x2 bricks
        },
        estimated_brick_count=76,
        typical_colors=["#FFFFFF", "#F5F5DC", "#D2B48C"],  # Light wood
        metadata={
            "style": "modern",
            "material": "simulated wood",
            "area": 64,
            "aspect_ratio": 1.0,
            "tags": ["furniture", "storage", "books", "corner"]
        }
    ),

    # ========================================================================
    # LAPTOPS (Tech/Decorative)
    # ========================================================================
    "laptop_compact_silver": LegoObjectDefinition(
        object_id="laptop_compact_silver",
        object_type="decorative",
        name="Compact Laptop (Silver)",
        signature="laptop_compact_silver_v1",
        dimensions=(6, 4, 1),  # 6w x 4d x 1h studs
        brick_composition={
            "3003": 2,    # 2x2 bricks
            "3004": 4,    # 1x2 bricks
            "3005": 6,    # 1x1 bricks
            "3068": 4,    # 2x2 tiles (screen)
        },
        estimated_brick_count=12,
        typical_colors=["#C0C0C0", "#D3D3D3", "#000000"],  # Silver/gray/black
        metadata={
            "style": "modern",
            "material": "simulated metal/plastic",
            "area": 24,
            "aspect_ratio": 1.5,
            "tags": ["decorative", "tech", "desk", "laptop", "compact"]
        }
    ),

    "laptop_gaming_rgb": LegoObjectDefinition(
        object_id="laptop_gaming_rgb",
        object_type="decorative",
        name="Gaming Laptop (RGB)",
        signature="laptop_gaming_rgb_v1",
        dimensions=(8, 5, 1),  # 8w x 5d x 1h studs
        brick_composition={
            "3001": 1,    # 2x4 brick (base)
            "3003": 3,    # 2x2 bricks
            "3004": 6,    # 1x2 bricks
            "3069": 4,    # 1x2 tiles
            "3068": 4,    # 2x2 tiles (screen)
        },
        estimated_brick_count=18,
        typical_colors=["#000000", "#FF0000", "#0000FF", "#00FF00"],  # Black with RGB
        metadata={
            "style": "gaming",
            "material": "simulated metal/RGB lighting",
            "area": 40,
            "aspect_ratio": 1.6,
            "tags": ["decorative", "tech", "gaming", "laptop", "large"]
        }
    ),

    # ========================================================================
    # BOOKS (Decorative/Accessories)
    # ========================================================================
    "book_hardcover_large": LegoObjectDefinition(
        object_id="book_hardcover_large",
        object_type="decorative",
        name="Hardcover Book (Large)",
        signature="book_hardcover_large_v1",
        dimensions=(4, 6, 2),  # 4w x 6d x 2h studs
        brick_composition={
            "3003": 2,    # 2x2 bricks
            "3069": 4,    # 1x2 tiles (pages)
            "3070": 2,    # 1x1 tiles (binding)
        },
        estimated_brick_count=8,
        typical_colors=["#8B0000", "#8B4513", "#00008B"],  # Book colors
        metadata={
            "style": "traditional",
            "material": "simulated paper/leather",
            "area": 24,
            "aspect_ratio": 0.67,
            "tags": ["decorative", "book", "hardcover", "shelf", "accent"]
        }
    ),

    "book_paperback_stack": LegoObjectDefinition(
        object_id="book_paperback_stack",
        object_type="decorative",
        name="Paperback Book Stack (3)",
        signature="book_paperback_stack_v1",
        dimensions=(3, 4, 3),  # 3w x 4d x 3h studs (stacked)
        brick_composition={
            "3068": 1,    # 2x2 tile (stack base)
            "3069": 3,    # 1x2 tiles
            "3070": 2,    # 1x1 tiles
        },
        estimated_brick_count=6,
        typical_colors=["#FFD700", "#FF6347", "#4169E1"],  # Book spine colors
        metadata={
            "style": "contemporary",
            "material": "simulated paper",
            "area": 12,
            "aspect_ratio": 0.75,
            "tags": ["decorative", "book", "paperback", "stack", "shelf"]
        }
    ),

    # ========================================================================
    # CHAIRS (Extended)
    # ========================================================================
    "chair_modern_white": LegoObjectDefinition(
        object_id="chair_modern_white",
        object_type="chair",
        name="Modern Chair (White)",
        signature="chair_modern_white_v1",
        dimensions=(4, 4, 8),  # 4w x 4d x 8h studs
        brick_composition={
            "3003": 8,    # 2x2 bricks (seat/back)
            "3004": 10,   # 1x2 bricks (legs/frame)
            "3005": 6,    # 1x1 bricks (details)
            "3938": 4,    # Hinge bricks (swivel joints)
        },
        estimated_brick_count=28,
        typical_colors=["#FFFFFF", "#D3D3D3"],  # White/light gray
        metadata={
            "style": "contemporary",
            "material": "simulated plastic",
            "area": 16,
            "aspect_ratio": 1.0,
            "tags": ["furniture", "seating", "office", "modern", "compact"]
        }
    ),

    "chair_gaming_red": LegoObjectDefinition(
        object_id="chair_gaming_red",
        object_type="chair",
        name="Gaming Chair (Red)",
        signature="chair_gaming_red_v1",
        dimensions=(4, 4, 10),  # 4w x 4d x 10h studs
        brick_composition={
            "3001": 4,    # 2x4 bricks (frame)
            "3003": 10,   # 2x2 bricks (back/seat)
            "3004": 12,   # 1x2 bricks (armrests)
            "3938": 10,   # Hinge bricks (articulation)
        },
        estimated_brick_count=36,
        typical_colors=["#FF0000", "#000000", "#808080"],  # Red/black/gray
        metadata={
            "style": "gaming",
            "material": "simulated leather/metal",
            "area": 16,
            "aspect_ratio": 1.0,
            "tags": ["furniture", "seating", "gaming", "high-back", "premium"]
        }
    ),

    "chair_office_ergonomic": LegoObjectDefinition(
        object_id="chair_office_ergonomic",
        object_type="chair",
        name="Ergonomic Office Chair",
        signature="chair_office_ergonomic_v1",
        dimensions=(4, 4, 9),  # 4w x 4d x 9h studs
        brick_composition={
            "3003": 10,   # 2x2 bricks
            "3004": 12,   # 1x2 bricks
            "3005": 8,    # 1x1 bricks
            "3938": 2,    # Hinge bricks (adjustment)
        },
        estimated_brick_count=32,
        typical_colors=["#000000", "#808080", "#FFFFFF"],  # Black/gray/white
        metadata={
            "style": "ergonomic",
            "material": "simulated mesh/plastic",
            "area": 16,
            "aspect_ratio": 1.0,
            "tags": ["furniture", "seating", "office", "ergonomic", "professional"]
        }
    ),

    # ========================================================================
    # DOORS (Architecture)
    # ========================================================================
    "door_single_oak": LegoObjectDefinition(
        object_id="door_single_oak",
        object_type="architecture",
        name="Single Door (Oak)",
        signature="door_single_oak_v1",
        dimensions=(4, 1, 10),  # 4w x 1d x 10h studs
        brick_composition={
            "3001": 6,    # 2x4 bricks (frame)
            "3004": 8,    # 1x2 bricks (trim)
            "3069": 8,    # 1x2 tiles (door panel)
            "3938": 4,    # Hinge bricks (opening)
        },
        estimated_brick_count=24,
        typical_colors=["#8B4513", "#D2B48C"],  # Oak brown tones
        metadata={
            "style": "traditional",
            "material": "simulated wood",
            "area": 4,
            "aspect_ratio": 4.0,
            "tags": ["architecture", "door", "entrance", "oak", "single"]
        }
    ),

    "door_double_white": LegoObjectDefinition(
        object_id="door_double_white",
        object_type="architecture",
        name="Double Doors (White)",
        signature="door_double_white_v1",
        dimensions=(8, 1, 10),  # 8w x 1d x 10h studs
        brick_composition={
            "3001": 12,   # 2x4 bricks (frame)
            "3003": 8,    # 2x2 bricks (corners)
            "3069": 16,   # 1x2 tiles (door panels)
            "3938": 8,    # Hinge bricks (double opening)
        },
        estimated_brick_count=48,
        typical_colors=["#FFFFFF", "#D3D3D3", "#808080"],  # White/gray
        metadata={
            "style": "contemporary",
            "material": "simulated composite",
            "area": 8,
            "aspect_ratio": 8.0,
            "tags": ["architecture", "door", "entrance", "double", "modern"]
        }
    ),

    "door_sliding_glass": LegoObjectDefinition(
        object_id="door_sliding_glass",
        object_type="architecture",
        name="Sliding Glass Door",
        signature="door_sliding_glass_v1",
        dimensions=(6, 1, 8),  # 6w x 1d x 8h studs
        brick_composition={
            "3001": 4,    # 2x4 bricks (frame)
            "3068": 4,    # 2x2 tiles (glass panels)
            "3004": 6,    # 1x2 bricks (trim)
            "3938": 2,    # Hinge bricks (sliding mechanism)
        },
        estimated_brick_count=16,
        typical_colors=["#C0C0C0", "#000000", "#87CEEB"],  # Silver/black/light blue
        metadata={
            "style": "modern",
            "material": "simulated glass/aluminum",
            "area": 6,
            "aspect_ratio": 6.0,
            "tags": ["architecture", "door", "sliding", "glass", "patio"]
        }
    ),

    "doorframe_interior": LegoObjectDefinition(
        object_id="doorframe_interior",
        object_type="architecture",
        name="Interior Doorframe",
        signature="doorframe_interior_v1",
        dimensions=(4, 2, 10),  # 4w x 2d x 10h studs (frame only)
        brick_composition={
            "3001": 8,    # 2x4 bricks (vertical supports)
            "3003": 6,    # 2x2 bricks (corners)
            "3004": 12,   # 1x2 bricks (trim)
            "3005": 6,    # 1x1 bricks (details)
        },
        estimated_brick_count=32,
        typical_colors=["#8B4513", "#FFFFFF", "#D3D3D3"],  # Wood/white trim
        metadata={
            "style": "traditional",
            "material": "simulated wood/plaster",
            "area": 8,
            "aspect_ratio": 2.0,
            "tags": ["architecture", "doorframe", "interior", "opening", "frame-only"]
        }
    ),
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_lego_object_by_id(object_id: str) -> Optional[LegoObjectDefinition]:
    """Retrieve a pre-defined LEGO object by ID"""
    return LEGO_OBJECTS_DATABASE.get(object_id)

def get_lego_objects_by_type(object_type: str) -> Dict[str, LegoObjectDefinition]:
    """Retrieve all LEGO objects of a specific type"""
    return {
        obj_id: obj_def
        for obj_id, obj_def in LEGO_OBJECTS_DATABASE.items()
        if obj_def.object_type == object_type
    }

def get_all_lego_object_ids() -> List[str]:
    """Get all available object IDs"""
    return list(LEGO_OBJECTS_DATABASE.keys())

def get_object_by_signature(signature: str) -> Optional[LegoObjectDefinition]:
    """Look up object by cluster signature"""
    for obj_def in LEGO_OBJECTS_DATABASE.values():
        if obj_def.signature == signature:
            return obj_def
    return None

def find_similar_objects(
    object_type: str,
    max_bricks: int = None,
    max_width: int = None
) -> List[Tuple[str, LegoObjectDefinition]]:
    """
    Find objects matching criteria (for intelligent substitution).
    
    Args:
        object_type: "desk", "bed", "shelf", etc.
        max_bricks: Maximum brick count allowed
        max_width: Maximum width in studs
        
    Returns:
        List of (object_id, definition) tuples matching criteria
    """
    results = []
    
    for obj_id, obj_def in LEGO_OBJECTS_DATABASE.items():
        if obj_def.object_type != object_type:
            continue
            
        if max_bricks and obj_def.estimated_brick_count > max_bricks:
            continue
            
        if max_width and obj_def.dimensions[0] > max_width:
            continue
            
        results.append((obj_id, obj_def))
    
    return sorted(results, key=lambda x: x[1].estimated_brick_count)

def get_brick_composition(object_id: str) -> Optional[Dict[str, int]]:
    """Get brick part IDs and quantities for an object"""
    obj = get_lego_object_by_id(object_id)
    return obj.brick_composition if obj else None

def get_total_brick_count(object_id: str) -> Optional[int]:
    """Get total brick count for an object"""
    obj = get_lego_object_by_id(object_id)
    return obj.estimated_brick_count if obj else None

def list_database_summary() -> str:
    """Generate a summary of available objects"""
    summary = "LEGO Objects Database Summary\n"
    summary += "=" * 50 + "\n\n"
    
    by_type = {}
    for obj_id, obj_def in LEGO_OBJECTS_DATABASE.items():
        if obj_def.object_type not in by_type:
            by_type[obj_def.object_type] = []
        by_type[obj_def.object_type].append((obj_id, obj_def))
    
    for obj_type in sorted(by_type.keys()):
        summary += f"\n{obj_type.upper()}\n"
        summary += "-" * 40 + "\n"
        for obj_id, obj_def in by_type[obj_type]:
            summary += f"  {obj_id}: {obj_def.name}\n"
            summary += f"    Size: {obj_def.dimensions[0]}x{obj_def.dimensions[1]}x{obj_def.dimensions[2]} studs\n"
            summary += f"    Bricks: {obj_def.estimated_brick_count}\n"
    
    return summary
