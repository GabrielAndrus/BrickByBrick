from pydantic import BaseModel
from typing import List, Optional


# ============ Object Analysis Schemas ============

class EstimatedDimensions(BaseModel):
    """Estimated dimensions in millimeters"""
    h: float  # height
    w: float  # width
    d: float  # depth


class VoxelPoint(BaseModel):
    """A single voxel point with position and color"""
    point: List[int]  # [x, y, z]
    color_hex: str


class RawVisionData(BaseModel):
    """Raw vision data from video analysis"""
    estimated_dimensions_mm: EstimatedDimensions
    voxel_cloud: List[VoxelPoint]
    confidence_score: float


class StructuralMetadata(BaseModel):
    """Structural metadata about the object"""
    is_airy: bool
    has_curves: bool
    missing_surfaces: List[str]


class ObjectAnalysisResponse(BaseModel):
    """Full object analysis response from TwelveLabs"""
    object_id: str
    raw_vision_data: RawVisionData
    structural_metadata: StructuralMetadata


# ============ Scenery Analysis Schemas ============

class GridDimensions(BaseModel):
    """Grid dimensions for the world"""
    x: int
    y: int
    z: int


class WorldMetadata(BaseModel):
    """Metadata about the LEGO world"""
    grid_unit: str
    total_dimensions: GridDimensions
    theme: str


class Brick(BaseModel):
    """A single LEGO brick placement"""
    part_id: str
    color_id: int
    pos: List[int]  # [x, y, z]
    type: str


class SceneryLayer(BaseModel):
    """A layer of scenery bricks"""
    layer_id: str
    bricks: List[Brick]


class Anchors(BaseModel):
    """Anchor points in the scenery"""
    road_center: List[int]
    flat_surface_zones: List[List[int]]


class SceneryAnalysisResponse(BaseModel):
    """Full scenery analysis response"""
    session_id: str
    world_metadata: WorldMetadata
    scenery_layers: List[SceneryLayer]
    anchors: Anchors


# ============ Legacy Schemas (kept for compatibility) ============

class Dimensions(BaseModel):
    """Dimensions in millimeters (legacy)"""
    height: float
    width: float
    depth: float


class Complexity(BaseModel):
    """Complexity flags for object analysis (legacy)"""
    is_airy: bool
    has_curves: bool
    has_floating_parts: bool
