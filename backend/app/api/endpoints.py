from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.services.master_builder import MasterBuilder
from app.api.lego_build_endpoint import router as lego_build_router
import tempfile
import os

# Optional Backboard import
try:
    from app.services.backboard_service import BackboardService
    BACKBOARD_AVAILABLE = True
except ImportError:
    BackboardService = None
    BACKBOARD_AVAILABLE = False

router = APIRouter(prefix="/api", tags=["API"])


class VoxelInput(BaseModel):
    """Input voxel data from Three.js"""
    x: int
    y: int
    z: int
    hex_color: str


class ProcessVoxelsRequest(BaseModel):
    """Request to process voxels and generate LEGO bricks"""
    voxels: List[VoxelInput]


@router.get("/test")
async def test_endpoint():
    """
    Test endpoint
    """
    return {"message": "API endpoints are working"}


@router.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file for processing.
    
    Accepts video files and returns a success message with file info.
    For demo purposes, this endpoint accepts the video and returns immediately.
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Get file size
        file_size = len(content)
        
        return JSONResponse({
            "status": "success",
            "message": "Video uploaded successfully",
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file_size,
            "temp_path": tmp_path
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading video: {str(e)}")


@router.post("/master-builder/process")
async def process_voxels(request: ProcessVoxelsRequest) -> Dict:
    """
    Process voxel data and generate MasterManifest with LEGO bricks.
    
    Takes a 3D array of voxels (x, y, z, hex_color) from Three.js and converts
    it into a list of real LEGO bricks using Greedy Fitting Algorithm.
    
    Features:
    - Greedy fitting: Tries largest bricks first (2x4, 2x2, 1x2, 1x1)
    - Laminar interlocking: Staggers bricks on even/odd layers
    - Color verification: Uses Rebrickable API to verify part availability
    - Fallback logic: If a brick is unavailable, tries next smaller size
    
    Returns MasterManifest with Part ID, Position, Rotation, Color ID, and is_verified flag.
    """
    try:
        builder = MasterBuilder()
        
        # Convert Pydantic models to dicts
        voxel_data = [
            {
                "x": voxel.x,
                "y": voxel.y,
                "z": voxel.z,
                "hex_color": voxel.hex_color
            }
            for voxel in request.voxels
        ]
        
        # Process voxels and generate manifest (async)
        manifest = await builder.process_voxels(voxel_data)
        
        return manifest
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing voxels: {str(e)}")


class ThreeJSMeshInput(BaseModel):
    """Three.js mesh input format"""
    vertices: List[List[float]]  # [[x, y, z], ...]
    faces: List[List[int]]  # [[i, j, k], ...]
    normals: Optional[List[List[float]]] = None
    colors: Optional[List[str]] = None


@router.post("/threejs/voxelize")
async def voxelize_threejs_mesh(mesh: ThreeJSMeshInput) -> Dict:
    """
    Convert a Three.js mesh to voxel grid.
    
    This endpoint accepts a Three.js mesh (vertices and faces) and returns
    a voxel grid that can be processed by the MasterBuilder.
    
    Note: The actual voxelization happens on the frontend using lib/voxelizer.ts.
    This endpoint is for server-side processing if needed.
    """
    try:
        # Convert Three.js mesh to voxel format
        # For now, return a placeholder - actual voxelization should happen client-side
        # using the voxelizer.ts utility
        
        voxels = []
        # Simple bounding box voxelization (placeholder)
        # In production, this would use proper raycasting
        
        return {
            "voxels": voxels,
            "message": "Use frontend lib/voxelizer.ts for proper mesh voxelization"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error voxelizing mesh: {str(e)}")


@router.get("/backboard/{thread_id}/instructions")
async def get_interactive_instructions(thread_id: str) -> Dict:
    """
    Get interactive instructions for a build session.
    
    Returns a timeline of Scene Deltas that the frontend can use to
    scrub through the "History of Creation" - every brick placement,
    model switch, and structural fix.
    
    Each delta tells the frontend which Three.js objects to show/hide.
    """
    if not BACKBOARD_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Backboard SDK is not available. Please install the Backboard SDK to use this endpoint."
        )
    
    try:
        service = BackboardService()
        timeline = service.get_instruction_timeline(thread_id)
        return timeline
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Backboard package not installed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting instructions: {str(e)}")


@router.get("/backboard/{thread_id}/deltas")
async def get_scene_deltas(thread_id: str) -> List[Dict]:
    """
    Get raw Scene Deltas for a thread.
    
    Returns the list of all scene changes (brick placements, model switches, etc.)
    in chronological order.
    """
    if not BACKBOARD_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Backboard SDK is not available. Please install the Backboard SDK to use this endpoint."
        )
    
    try:
        service = BackboardService()
        deltas = service.get_interactive_instructions(thread_id)
        return deltas
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Backboard package not installed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting deltas: {str(e)}")
