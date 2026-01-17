import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.services.twelve_labs import TwelveLabsService
from app.models.schemas import ObjectAnalysisResponse, SceneryAnalysisResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Global service instance (initialized lazily)
_twelve_labs_service: TwelveLabsService | None = None


def get_twelve_labs_service() -> TwelveLabsService:
    """Get or create the TwelveLabs service instance."""
    global _twelve_labs_service
    if _twelve_labs_service is None:
        _twelve_labs_service = TwelveLabsService()
    return _twelve_labs_service


@router.get("/test")
async def test_endpoint():
    """Test endpoint"""
    return {"message": "API endpoints are working"}


@router.post("/upload-video", response_model=dict)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file and index it with TwelveLabs.
    
    Returns the video_id for subsequent analysis.
    """
    # Validate file type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        service = get_twelve_labs_service()
        
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Ensure index exists and upload video
            service.ensure_index_exists()
            video_id = service.upload_and_index(tmp_path)
            
            return {
                "status": "success",
                "video_id": video_id,
                "message": "Video uploaded and indexed successfully"
            }
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error uploading video: {e}")
        raise HTTPException(status_code=500, detail="Failed to process video")


@router.post("/analyze/{video_id}", response_model=ObjectAnalysisResponse)
async def analyze_video(video_id: str):
    """
    Analyze an indexed video to extract object dimensions, colors, and complexity.
    """
    try:
        service = get_twelve_labs_service()
        result = service.analyze_object(video_id)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error analyzing video: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze video")


@router.post("/process-video", response_model=dict)
async def process_video(file: UploadFile = File(...)):
    """
    Full pipeline: Upload, index, and analyze a video in one request.
    
    Returns the complete analysis results.
    """
    # Validate file type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    tmp_path = None
    try:
        service = get_twelve_labs_service()
        
        # Save uploaded file to temp location
        content = await file.read()
        
        # Log file size for debugging
        logger.info(f"Received video file: {file.filename}, size: {len(content)} bytes, type: {file.content_type}")
        
        if len(content) < 1000:
            raise HTTPException(status_code=400, detail="Video file is too small or empty")
        
        # Get original extension from filename
        original_ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        if not original_ext:
            original_ext = ".mp4"
            
        # Create temp file with proper extension
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=original_ext)
        try:
            os.write(tmp_fd, content)
        finally:
            os.close(tmp_fd)
        
        logger.info(f"Saved temp file: {tmp_path}, size on disk: {os.path.getsize(tmp_path)} bytes")
        
        # Full pipeline
        service.ensure_index_exists()
        video_id = service.upload_and_index(tmp_path)
        analysis = service.analyze_object(video_id)
        
        return {
            "status": "success",
            "video_id": video_id,
            "analysis": analysis.model_dump()
        }
                
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing video: {e}")
        raise HTTPException(status_code=500, detail="Failed to process video")
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/process-scenery", response_model=dict)
async def process_scenery(file: UploadFile = File(...), theme: str = "urban_park"):
    """
    Process a scenery video: Upload, index, and analyze for LEGO world building.
    
    Returns scenery analysis with world metadata, brick layers, and anchors.
    """
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    tmp_path = None
    try:
        service = get_twelve_labs_service()
        
        content = await file.read()
        logger.info(f"Received scenery video: {file.filename}, size: {len(content)} bytes")
        
        if len(content) < 1000:
            raise HTTPException(status_code=400, detail="Video file is too small or empty")
        
        original_ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        if not original_ext:
            original_ext = ".mp4"
            
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=original_ext)
        try:
            os.write(tmp_fd, content)
        finally:
            os.close(tmp_fd)
        
        logger.info(f"Saved temp file: {tmp_path}, size on disk: {os.path.getsize(tmp_path)} bytes")
        
        service.ensure_index_exists()
        video_id = service.upload_and_index(tmp_path)
        analysis = service.analyze_scenery(video_id, theme=theme)
        
        return {
            "status": "success",
            "video_id": video_id,
            "analysis": analysis.model_dump()
        }
                
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing scenery: {e}")
        raise HTTPException(status_code=500, detail="Failed to process scenery")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
