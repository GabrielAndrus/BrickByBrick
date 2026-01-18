"""
API Endpoints for Reality-to-Brick

Full Pipeline:
1. Upload video 
2. Extract frames (FFmpeg)
3. Get scene description (TwelveLabs)
4. Generate ThreeJS code (Gemini)
"""

import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.twelve_labs import get_twelve_labs_api
from app.services.ffmpeg_processor import get_ffmpeg_processor
from app.services.gemini_service import get_gemini_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "API is running"}


@router.get("/test-services")
async def test_services():
    """Test if TwelveLabs and Gemini are configured"""
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    results = {
        "twelvelabs": {
            "api_key_set": bool(os.getenv("TWELVE_LABS_API_KEY") or os.getenv("TWL_API_KEY")),
            "index_id_set": bool(os.getenv("TWL_INDEX_ID")),
        },
        "gemini": {
            "api_key_set": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
        }
    }
    
    # Test TwelveLabs connection
    try:
        api = get_twelve_labs_api()
        results["twelvelabs"]["initialized"] = True
        results["twelvelabs"]["index_id"] = api.index_id[:8] + "..." if api.index_id else None
    except Exception as e:
        results["twelvelabs"]["initialized"] = False
        results["twelvelabs"]["error"] = str(e)
    
    # Test Gemini connection
    try:
        gemini = get_gemini_service()
        results["gemini"]["initialized"] = True
        results["gemini"]["model"] = str(gemini.model.model_name) if gemini.model else None
        
        # List available models
        try:
            import google.generativeai as genai
            available = [m.name.split('/')[-1] for m in genai.list_models() 
                        if 'generateContent' in m.supported_generation_methods]
            results["gemini"]["available_models"] = available
        except Exception as e:
            results["gemini"]["available_models_error"] = str(e)
    except Exception as e:
        results["gemini"]["initialized"] = False
        results["gemini"]["error"] = str(e)
    
    return results


@router.post("/process-video")
async def process_video(file: UploadFile = File(...), num_frames: int = 6):
    """
    Full pipeline: 
    1. Extract frames (FFmpeg) for display
    2. Send video to TwelveLabs (get extremely detailed description + frames/angles)
    3. Send video directly to Gemini (generate ThreeJS from video)
    
    Returns:
    - Extracted frames (base64 images)
    - Extremely detailed scene description from TwelveLabs
    - ThreeJS code from Gemini (generated from video)
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
        
        # Step 2: Try TwelveLabs (optional - may fail if index doesn't support analyze)
        logger.info("Step 2: Attempting TwelveLabs analysis...")
        api = get_twelve_labs_api()
        
        video_id = None
        description = None
        timestamps = None
        twelvelabs_success = False
        
        try:
            upload = await api.upload_video(tmp_path)
            video_id = upload.get("video_id")
            task_id = upload.get("task_id")
            
            # Wait for task completion (shorter timeout)
            logger.info("Waiting for indexing...")
            await api.wait_for_task(task_id, timeout=60)
            
            # Wait for video to be ready (shorter timeout)
            logger.info("Waiting for video ready...")
            await api.wait_for_video_ready(video_id, timeout=60)
            
            # Get scene description
            logger.info("Step 3: Getting scene description...")
            description = await api.get_object_description(video_id)
            
            # Get view timestamps
            logger.info("Step 4: Getting view timestamps...")
            timestamps = await api.get_all_view_timestamps(video_id)
            twelvelabs_success = True
            
        except Exception as e:
            logger.warning(f"TwelveLabs failed (will use Gemini only): {e}")
            description = None  # Let Gemini analyze from images
            timestamps = None
        
        # Step 5: Generate ThreeJS with Gemini (send video directly)
        logger.info("Step 5: Generating ThreeJS with Gemini from video...")
        threejs_code = None
        
        try:
            gemini = get_gemini_service()
            # Send video directly to Gemini, optionally include TwelveLabs description for context
            scene_desc = description if twelvelabs_success and description else None
            
            threejs_code = await gemini.generate_threejs_from_video(
                video_path=tmp_path,
                scene_description=scene_desc
            )
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            threejs_code = f"// Error generating ThreeJS: {e}"
        
        return {
            "status": "success",
            "video_id": video_id,
            "frames": {
                "count": len(frames),
                "video_duration": frames_result.get("video_duration"),
                "images": frames
            },
            "analysis": {
                "twelvelabs_success": twelvelabs_success,
                "description": description if description else "TwelveLabs analysis skipped - Gemini analyzing images directly",
                "timestamps": timestamps if timestamps else {}
            },
            "threejs": {
                "code": threejs_code
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
    """Extract frames only (no TwelveLabs or Gemini)"""
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


@router.post("/generate-threejs")
async def generate_threejs_from_description(description: str):
    """Generate ThreeJS from description only (no images)"""
    try:
        gemini = get_gemini_service()
        code = await gemini.generate_threejs_simple(description)
        
        return {
            "status": "success",
            "threejs": {"code": code}
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(500, str(e))


# Backwards compatibility
@router.post("/process-video-with-frames")
async def process_video_with_frames(file: UploadFile = File(...), num_frames: int = 6):
    """Alias for /process-video"""
    return await process_video(file, num_frames)
