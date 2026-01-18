"""
LEGO Build Generation API Endpoint

Main entry point that:
1. Accepts Three.js voxel data
2. Uses Greedy algorithm with hardcoded LEGO objects
3. Generates detailed JSON manifest with position, vertex, and LEGO type
4. Uses Backboard memory for persistent storage
5. Provides component recommendations using Backboard's similarity matching
6. Minimizes variety in future creations through intelligent reuse
"""

import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from app.services.master_builder import MasterBuilder
from app.services.backboard_lego_memory import BackboardLegoMemory, LegoBuildOrchestrator
from app.services.lego_objects_database import get_lego_object_by_id
from app.services.piece_counter import PieceCounter
from app.services.instruction_manual_generator import InstructionManualGenerator

logger = logging.getLogger(__name__)

# Initialize routers
router = APIRouter(prefix="/api/lego", tags=["lego_build"])

# Global instances (in production, use dependency injection)
_backboard_memory: Optional[BackboardLegoMemory] = None
_orchestrator: Optional[LegoBuildOrchestrator] = None


# Request/Response Models
class VoxelData(BaseModel):
    """Single voxel from Three.js"""
    x: int
    y: int
    z: int
    hex_color: str


class ThreeJsVoxelInput(BaseModel):
    """Three.js voxel data input"""
    project_name: str
    room_type: str = "generic"  # bedroom, office, living room, etc.
    voxels: List[VoxelData]
    user_id: str = "default"
    metadata: Optional[Dict] = None


class BrickDetail(BaseModel):
    """Detailed brick information in output"""
    brick_id: str
    part_id: str
    lego_type: str
    position: Dict  # Both studs and mm
    dimensions: Dict
    rotation: int
    color_id: int
    color_info: Dict
    vertices: List[List[float]]  # 8 corner points
    voxel_coverage: List[List[int]]  # Which voxels covered
    is_verified: bool


class ComponentRecommendation(BaseModel):
    """Component recommendation from vector database"""
    component_id: str
    component_type: str
    similarity_score: float
    brick_count: int
    usage_count: int
    confirmed: bool
    reason: str


class LegoManifestResponse(BaseModel):
    """Complete LEGO build manifest response"""
    build_id: str
    project_name: str
    room_type: str
    generation_date: str
    total_bricks: int
    manifest_version: str
    bricks: List[BrickDetail]
    inventory: List[Dict]
    layers: Dict
    voxel_coverage: List[Dict]
    generation_metadata: Dict
    seam_map: Optional[List[Dict]]
    piece_count: Dict
    estimated_cost: float
    recommendations: List[ComponentRecommendation]


def init_lego_services(user_id: str = "default"):
    """Initialize LEGO services on startup"""
    global _backboard_memory, _orchestrator
    
    logger.info(f"Initializing LEGO services for user {user_id}")
    
    _backboard_memory = BackboardLegoMemory(user_id=user_id)
    _orchestrator = LegoBuildOrchestrator(user_id=user_id)


@router.post("/build/from-threejs", response_model=LegoManifestResponse)
async def generate_lego_build_from_threejs(
    input_data: ThreeJsVoxelInput = Body(..., description="Three.js voxel data")
) -> Dict:
    """
    Generate LEGO build from Three.js voxel data.
    
    PROCESS:
    1. Accept Three.js voxels (x, y, z, hex_color)
    2. Apply Greedy algorithm to fit LEGO bricks
    3. Reference hardcoded LEGO objects if components detected
    4. Generate detailed JSON with:
       - Part ID (LEGO brick type)
       - Position (x, y, z) in studs and mm
       - Rotation in degrees
       - Color information
       - Vertex positions (3D corners)
       - Voxel coverage map
    5. Store in Backboard memory
    6. Query vector database for similar components
    7. Provide recommendations to minimize variety
    
    Args:
        input_data: Three.js voxel input
        
    Returns:
        Detailed LEGO manifest with recommendations
    """
    
    try:
        logger.info(f"Processing LEGO build: {input_data.project_name}")
        logger.debug(f"Voxel count: {len(input_data.voxels)}")
        
        # Initialize services if needed
        if _backboard_memory is None:
            init_lego_services(input_data.user_id)
        
        # Convert Three.js voxels to format MasterBuilder expects
        voxel_data = [
            {
                "x": v.x,
                "y": v.y,
                "z": v.z,
                "hex_color": v.hex_color
            }
            for v in input_data.voxels
        ]
        
        # Step 1: Generate build with MasterBuilder (greedy algorithm)
        logger.info("Step 1: Running Greedy algorithm")
        master_builder = MasterBuilder()
        manifest = master_builder.process_voxels_sync(voxel_data)
        
        # Get piece count and cost
        piece_summary = master_builder.get_piece_count()
        logger.info(f"Step 2: Piece count complete - {piece_summary.total_pieces} total pieces")
        
        # Generate instruction manual
        logger.info("Step 2.5: Generating instruction manual")
        build_guide = InstructionManualGenerator.generate_build_guide(manifest, input_data.project_name)
        logger.info(f"Generated {build_guide.total_steps} instruction steps")
        
        # Step 2: Query hardcoded database for component references
        logger.info("Step 3: Querying hardcoded LEGO objects database")
        # This is already done in MasterBuilder._query_hardcoded_database()
        
        # Step 3: Check for detected components in evolved_components
        detected_components = manifest.get("evolved_components", [])
        logger.info(f"Detected {len(detected_components)} component signatures")
        
        # Step 4: Get recommendations from Backboard memory (similarity search)
        logger.info("Step 4: Querying Backboard for similar components")
        recommendations = []
        
        if _backboard_memory and detected_components:
            # Query Backboard for similar builds in the same room
            similar_builds = _backboard_memory.get_similar_builds(
                project_name=input_data.project_name,
                room_type=input_data.room_type,
                max_results=5
            )
            
            # Extract component recommendations from similar builds
            for similar_build in similar_builds:
                if similar_build.get("components"):
                    for component in similar_build["components"][:3]:  # Top 3 components
                        recommendations.append({
                            "component_id": component.get("component_id", "similar_component"),
                            "component_type": component.get("component_type", "generic"),
                            "similarity_score": similar_build.get("similarity", 0.8),
                            "brick_count": component.get("brick_count", 0),
                            "usage_count": component.get("usage_count", 0),
                            "confirmed": True,
                            "reason": f"Similar {component.get('component_type', 'component')} from {similar_build.get('project_name', 'previous build')} in {input_data.room_type}"
                        })
        
        # Step 5: Save to Backboard memory
        logger.info("Step 5: Saving build to Backboard memory")
        build_id = _backboard_memory.save_build(
            project_name=input_data.project_name,
            voxel_data={
                "voxel_count": len(input_data.voxels),
                "voxels": voxel_data[:100]  # Save first 100 for size limit
            },
            manifest=manifest,
            piece_summary={
                "total_pieces": piece_summary.total_pieces,
                "total_unique_pieces": piece_summary.total_unique_pieces,
                "estimated_cost": piece_summary.estimated_cost
            },
            components=recommendations,
            room_type=input_data.room_type,
            metadata=input_data.metadata or {}
        )
        
        # Step 6: Build response
        logger.info(f"Step 6: Building response for build {build_id}")
        
        # Convert build guide steps to dict format
        build_steps = [
            {
                "step_number": step.step_number,
                "layer_z": step.layer_z,
                "bricks_in_step": step.bricks_in_step,
                "piece_counts": step.piece_counts,
                "instructions": step.instructions
            }
            for step in build_guide.steps
        ]
        
        # Calculate baseplate size
        max_x = max([brick["position"]["studs"][0] + brick["dimensions"]["studs"]["width"] for brick in manifest.get("bricks", [])], default=0)
        max_y = max([brick["position"]["studs"][1] + brick["dimensions"]["studs"]["depth"] for brick in manifest.get("bricks", [])], default=0)
        baseplate_info = {
            "size_studs": [max_x + 2, max_y + 2],  # Add 2 studs padding
            "size_mm": [(max_x + 2) * 8, (max_y + 2) * 8],
            "part_id": "3811",  # Standard baseplate
            "lego_type": "Baseplate 32x32",
            "color_id": 16,  # Dark tan
            "quantity": 1
        }
        
        response = {
            "build_id": build_id,
            "project_name": input_data.project_name,
            "room_type": input_data.room_type,
            "generation_date": manifest.get("generation_metadata", {}).get("generation_date", ""),
            "total_bricks": manifest.get("total_bricks", 0),
            "manifest_version": manifest.get("manifest_version", "2.0"),
            "bricks": manifest.get("bricks", []),
            "inventory": manifest.get("inventory", []),
            "layers": manifest.get("layers", {}),
            "voxel_coverage": manifest.get("voxel_coverage", []),
            "generation_metadata": manifest.get("generation_metadata", {}),
            "seam_map": manifest.get("seam_map", []),
            "piece_count": {
                "total_pieces": piece_summary.total_pieces,
                "total_unique": piece_summary.total_unique_pieces,
                "breakdown": [
                    {
                        "part_id": pc.part_id,
                        "color_id": pc.color_id,
                        "quantity": pc.quantity,
                        "piece_name": pc.piece_name
                    }
                    for pc in piece_summary.piece_counts[:20]  # Top 20
                ]
            },
            "estimated_cost": piece_summary.estimated_cost,
            "recommendations": recommendations,
            "instruction_manual": {
                "total_steps": build_guide.total_steps,
                "difficulty": build_guide.difficulty,
                "estimated_time_minutes": build_guide.estimated_time_minutes,
                "baseplate": baseplate_info,
                "steps": build_steps,
                "layer_summary": build_guide.layer_summary
            }
        }
        
        logger.info(f"Successfully generated build {build_id}: {input_data.project_name}")
        return response
    
    except Exception as e:
        logger.error(f"Error generating LEGO build: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Build generation failed: {str(e)}")


@router.get("/builds/{build_id}")
async def get_build(build_id: str) -> Dict:
    """Retrieve a saved build from Backboard memory"""
    try:
        if _backboard_memory is None:
            init_lego_services()
        
        build = _backboard_memory.get_build(build_id)
        if not build:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
        
        return build.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving build: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/builds/room/{room_type}")
async def get_builds_by_room(room_type: str) -> List[Dict]:
    """Get all builds for a specific room type"""
    try:
        if _backboard_memory is None:
            init_lego_services()
        
        builds = _backboard_memory.get_builds_by_room(room_type)
        return [build.to_dict() for build in builds]
    
    except Exception as e:
        logger.error(f"Error retrieving builds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-builds")
async def get_recent_builds(limit: int = 10) -> List[Dict]:
    """Get recent builds"""
    try:
        if _backboard_memory is None:
            init_lego_services()
        
        builds = _backboard_memory.get_recent_builds(limit)
        return [build.to_dict() for build in builds]
    
    except Exception as e:
        logger.error(f"Error retrieving recent builds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_user_statistics() -> Dict:
    """Get user statistics from Backboard"""
    try:
        if _backboard_memory is None:
            init_lego_services()
        
        return _backboard_memory.get_statistics()
    
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/component-library")
async def get_component_library(component_type: str = None) -> Dict:
    """Get component library"""
    try:
        if _backboard_memory is None:
            init_lego_services()
        
        if component_type:
            components = _backboard_memory.get_library_by_type(component_type)
        else:
            components = _backboard_memory.component_library
        
        return {"components": components}
    
    except Exception as e:
        logger.error(f"Error retrieving component library: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-memory")
async def export_memory(filepath: str) -> Dict:
    """Export Backboard memory to file"""
    try:
        if _backboard_memory is None:
            init_lego_services()
        
        success = _backboard_memory.export_memory(filepath)
        
        if success:
            return {"status": "success", "filepath": filepath}
        else:
            raise HTTPException(status_code=500, detail="Failed to export memory")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting memory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict:
    """Health check endpoint"""
    try:
        if _backboard_memory is None:
            init_lego_services()
        
        stats = _backboard_memory.get_statistics()
        
        return {
            "status": "healthy",
            "service": "LEGO Build Generator with Backboard Memory",
            "builds_saved": stats.get("total_builds", 0),
            "components_in_library": stats.get("total_library_components", 0),
            "features": [
                "Greedy algorithm LEGO placement",
                "Hardcoded object reference (27 objects)",
                "Detailed JSON manifest with vertices",
                "Backboard persistent memory",
                "Backboard-powered similarity matching",
                "Automatic recommendations",
                "Multi-room support"
            ]
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "degraded",
            "error": str(e)
        }
