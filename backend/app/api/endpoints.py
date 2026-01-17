"""
API Endpoints for Reality-to-Brick
"""

import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.twelve_labs import get_twelve_labs_api
from app.services.ffmpeg_processor import get_ffmpeg_processor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "API is running"}


@router.post("/process-video")
async def process_video(file: UploadFile = File(...), num_frames: int = 6):
    """
    Main endpoint: Upload video, extract frames, get TwelveLabs analysis.
    
    Returns:
    - Extracted frames (base64 images)
    - Object description from TwelveLabs
    - View timestamps (front, side, back, top)
    """
    allowed = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    if file.content_type not in allowed:
        raise HTTPException(400, f"Invalid type. Allowed: {allowed}")
    
    tmp_path = None
    try:
        content = await file.read()
        logger.info(f"Processing: {file.filename}, {len(content)} bytes")
        
        if len(content) < 1000:
            raise HTTPException(400, "File too small")
        
        ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext or ".mp4")
        os.write(tmp_fd, content)
        os.close(tmp_fd)
        
        # Step 1: Extract frames with FFmpeg
        logger.info("Step 1: Extracting frames...")
        ffmpeg = get_ffmpeg_processor()
        frames_result = ffmpeg.extract_frames(tmp_path, num_frames=num_frames)
        frames = frames_result.get("images", [])
        logger.info(f"Extracted {len(frames)} frames")
        
        # Step 2: Upload to TwelveLabs
        logger.info("Step 2: Uploading to TwelveLabs...")
        api = get_twelve_labs_api()
        
        video_id = None
        description = None
        timestamps = None
        
        try:
            upload = await api.upload_video(tmp_path)
            video_id = upload.get("video_id")
            task_id = upload.get("task_id")
            
            # Wait for task completion
            logger.info("Waiting for indexing...")
            await api.wait_for_task(task_id, timeout=120)
            
            # Wait for video to be ready for analysis
            logger.info("Waiting for video ready...")
            await api.wait_for_video_ready(video_id, timeout=120)
            
            # Step 3: Get object description
            logger.info("Step 3: Getting object description...")
            description = await api.get_object_description(video_id)
            
            # Step 4: Get view timestamps
            logger.info("Step 4: Getting view timestamps...")
            timestamps = await api.get_all_view_timestamps(video_id)
            
        except Exception as e:
            logger.error(f"TwelveLabs error: {e}")
            description = f"Error: {e}"
            timestamps = {"error": str(e)}
        
        return {
            "status": "success",
            "video_id": video_id,
            "frames": {
                "count": len(frames),
                "video_duration": frames_result.get("video_duration"),
                "images": frames
            },
            "analysis": {
                "description": description,
                "timestamps": timestamps
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(500, str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/extract-frames")
async def extract_frames(file: UploadFile = File(...), num_frames: int = 6):
    """Extract frames only (no TwelveLabs)"""
    allowed = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    if file.content_type not in allowed:
        raise HTTPException(400, f"Invalid type. Allowed: {allowed}")
    
    tmp_path = None
    try:
        content = await file.read()
        if len(content) < 1000:
            raise HTTPException(400, "File too small")
        
        ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext or ".mp4")
        os.write(tmp_fd, content)
        os.close(tmp_fd)
        
        ffmpeg = get_ffmpeg_processor()
        result = ffmpeg.extract_frames(tmp_path, num_frames=num_frames)
        
        return {
            "status": "success",
            "num_frames": len(result.get("images", [])),
            "video_duration": result.get("video_duration"),
            "frames": result.get("images", [])
        }
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# Backwards compatibility
@router.post("/process-video-with-frames")
async def process_video_with_frames(file: UploadFile = File(...), num_frames: int = 6):
    """Alias for /process-video"""
    return await process_video(file, num_frames)
