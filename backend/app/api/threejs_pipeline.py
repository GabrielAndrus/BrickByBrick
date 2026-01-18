"""
Three.js to Backboard Pipeline Endpoint

Transfer Three.js scene data through Backboard's LEGO system:
Three.js → Voxelizer → Greedy Algorithm → LEGO Manifest → Backboard Memory
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel

from app.services.threejs_voxelizer import convert_threejs_to_voxels, get_sample_dorm_room_voxels
from app.services.backboard_lego_memory import BackboardLegoMemory
from app.services.master_builder import MasterBuilder

router = APIRouter(prefix="/api/lego", tags=["LEGO Build"])

# Global services (initialized at startup)
_backboard_memory: Optional[BackboardLegoMemory] = None
_master_builder: Optional[MasterBuilder] = None


class ThreeJsSceneInput(BaseModel):
    """Three.js scene as JSON"""
    objects: List[Dict]  # Scene objects with type, position, dimensions, color
    project_name: str = "three-js-project"
    room_type: str = "room"
    resolution: float = 0.15  # Voxel resolution in meters


class VoxelGridInput(BaseModel):
    """Already-voxelized input"""
    voxels: List[Dict]  # [{x, y, z, hex_color}, ...]
    project_name: str = "voxel-project"
    room_type: str = "room"


class PipelineResponse(BaseModel):
    """Complete pipeline response"""
    status: str
    voxels: List[Dict]
    manifest: Dict
    backboard_saved: bool
    recommendations: List[Dict]


# ============================================================================
# PIPELINE ENDPOINTS
# ============================================================================

@router.post("/threejs-to-backboard", response_model=PipelineResponse)
async def threejs_to_backboard(scene_input: ThreeJsSceneInput) -> PipelineResponse:
    """
    Complete pipeline: Three.js → Voxels → LEGO → Backboard
    
    Takes a Three.js scene description and processes it through the full pipeline:
    1. Convert Three.js geometry to voxel grid
    2. Apply greedy algorithm to generate LEGO build
    3. Generate detailed JSON manifest
    4. Save build to Backboard memory
    5. Query Backboard for similar builds (recommendations)
    
    Example scene_input:
    {
        "objects": [
            {
                "type": "BoxGeometry",
                "position": [0, 0, 0],
                "dimensions": {"width": 1, "height": 2, "depth": 1},
                "color": "0x888888"
            }
        ],
        "project_name": "my-room",
        "room_type": "bedroom"
    }
    """
    try:
        if not _master_builder or not _backboard_memory:
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        # Step 1: Convert Three.js to voxels
        voxels = convert_threejs_to_voxels(scene_input.dict(), scene_input.resolution)
        
        if not voxels:
            raise HTTPException(status_code=400, detail="No voxels generated from scene")
        
        # Step 2: Generate LEGO manifest using process_voxels_sync
        manifest = _master_builder.process_voxels_sync(voxels)
        
        # Step 3: Save to Backboard
        saved = _backboard_memory.save_build(
            project_name=scene_input.project_name,
            room_type=scene_input.room_type,
            voxels=voxels,
            manifest=manifest
        )
        
        # Step 4: Get recommendations from Backboard
        similar_builds = _backboard_memory.get_similar_builds(
            project_name=scene_input.project_name,
            room_type=scene_input.room_type,
            max_results=3
        )
        
        recommendations = []
        for build in similar_builds:
            recommendations.append({
                "project_name": build.get("project_name"),
                "similarity": build.get("similarity", 0.8),
                "brick_count": len(build.get("manifest", {}).get("bricks", []))
            })
        
        return PipelineResponse(
            status="success",
            voxels=voxels,
            manifest=manifest,
            backboard_saved=saved,
            recommendations=recommendations
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voxels-to-backboard", response_model=PipelineResponse)
async def voxels_to_backboard(voxel_input: VoxelGridInput) -> PipelineResponse:
    """
    Process already-voxelized data through Backboard.
    
    Skips the Three.js conversion step if you already have voxels.
    """
    try:
        if not _master_builder or not _backboard_memory:
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        # Step 1: Generate LEGO manifest using process_voxels_sync
        manifest = _master_builder.process_voxels_sync(voxel_input.voxels)
        
        # Step 2: Save to Backboard
        saved = _backboard_memory.save_build(
            project_name=voxel_input.project_name,
            room_type=voxel_input.room_type,
            voxels=voxel_input.voxels,
            manifest=manifest
        )
        
        # Step 3: Get recommendations
        similar_builds = _backboard_memory.get_similar_builds(
            project_name=voxel_input.project_name,
            room_type=voxel_input.room_type,
            max_results=3
        )
        
        recommendations = []
        for build in similar_builds:
            recommendations.append({
                "project_name": build.get("project_name"),
                "similarity": build.get("similarity", 0.8),
                "brick_count": len(build.get("manifest", {}).get("bricks", []))
            })
        
        return PipelineResponse(
            status="success",
            voxels=voxel_input.voxels,
            manifest=manifest,
            backboard_saved=saved,
            recommendations=recommendations
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SAMPLE DATA ENDPOINT
# ============================================================================

@router.get("/sample-dorm-room/voxels")
async def get_dorm_room_voxels() -> Dict:
    """
    Get voxel data for sample dorm room (no processing).
    
    Returns raw voxel grid extracted from the sample Three.js scene.
    """
    voxels = get_sample_dorm_room_voxels()
    return {
        "status": "success",
        "voxel_count": len(voxels),
        "voxels": voxels
    }


@router.post("/sample-dorm-room/process")
async def process_dorm_room_to_backboard() -> PipelineResponse:
    """
    Process the sample dorm room through the complete pipeline.
    
    This is a test endpoint that:
    1. Extracts voxels from the sample Three.js dorm room
    2. Generates LEGO manifest
    3. Saves to Backboard memory
    4. Returns recommendations for similar builds
    """
    try:
        if not _master_builder or not _backboard_memory:
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        # Get voxels from sample dorm room
        voxels = get_sample_dorm_room_voxels()
        
        # Generate manifest using process_voxels_sync
        manifest = _master_builder.process_voxels_sync(voxels)
        
        # Save to Backboard
        saved = _backboard_memory.save_build(
            project_name="sample-dorm-room",
            room_type="bedroom",
            voxels=voxels,
            manifest=manifest
        )
        
        # Get recommendations
        similar_builds = _backboard_memory.get_similar_builds(
            project_name="sample-dorm-room",
            room_type="bedroom",
            max_results=3
        )
        
        recommendations = []
        for build in similar_builds:
            recommendations.append({
                "project_name": build.get("project_name"),
                "similarity": build.get("similarity", 0.8),
                "brick_count": len(build.get("manifest", {}).get("bricks", []))
            })
        
        return PipelineResponse(
            status="success",
            voxels=voxels,
            manifest=manifest,
            backboard_saved=saved,
            recommendations=recommendations
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_threejs_services(backboard_memory: BackboardLegoMemory, 
                         master_builder: MasterBuilder):
    """Initialize services for Three.js pipeline"""
    global _backboard_memory, _master_builder
    _backboard_memory = backboard_memory
    _master_builder = master_builder
