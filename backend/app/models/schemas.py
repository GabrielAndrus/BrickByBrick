from pydantic import BaseModel
from typing import List


class Dimensions(BaseModel):
    """Dimensions in millimeters"""
    height: float
    width: float
    depth: float


class Complexity(BaseModel):
    """Complexity flags for object analysis"""
    is_airy: bool
    has_curves: bool
    has_floating_parts: bool


class ObjectAnalysisResponse(BaseModel):
    """Structured analysis response from TwelveLabs Pegasus engine"""
    dimensions_mm: Dimensions
    dominant_colors: List[str]  # Hex color strings
    complexity: Complexity
