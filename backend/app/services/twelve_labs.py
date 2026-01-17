"""
TwelveLabs Visual Intelligence Service
Based on working pipeline implementation
"""

import httpx
import asyncio
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TwelveLabsAPI:
    """TwelveLabs API client - requires TWL_INDEX_ID to be set"""
    
    def __init__(self):
        self.api_key = os.getenv("TWELVE_LABS_API_KEY") or os.getenv("TWL_API_KEY")
        self.index_id = os.getenv("TWL_INDEX_ID")
        self.base_url = "https://api.twelvelabs.io/v1.3"
        
        if not self.api_key:
            raise ValueError("TWL_API_KEY environment variable is required")
        if not self.index_id:
            raise ValueError("TWL_INDEX_ID environment variable is required")
        
        self.headers = {"x-api-key": self.api_key}
    
    # ========== VIDEO UPLOAD ==========
    
    async def upload_video(self, video_path: str) -> Dict[str, Any]:
        """Upload video file to TwelveLabs"""
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        mime_types = {".mov": "video/quicktime", ".mp4": "video/mp4", 
                      ".avi": "video/x-msvideo", ".webm": "video/webm"}
        ext = Path(video_path).suffix.lower()
        mime = mime_types.get(ext, "video/mp4")
        
        with open(video_path, "rb") as f:
            files = {
                "index_id": (None, self.index_id),
                "video_file": (Path(video_path).name, f, mime),
            }
            
            async with httpx.AsyncClient() as client:
                logger.info(f"Uploading: {video_path}")
                response = await client.post(
                    f"{self.base_url}/tasks",
                    headers=self.headers,
                    files=files,
                    timeout=120.0
                )
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"Upload failed: {response.text}")
                
                data = response.json()
                logger.info(f"Upload success: task={data.get('_id')}, video={data.get('video_id')}")
                return {"task_id": data.get("_id"), "video_id": data.get("video_id")}
    
    # ========== POLLING ==========
    
    async def wait_for_task(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Poll task until completed"""
        url = f"{self.base_url}/tasks/{task_id}"
        max_attempts = timeout // 3
        
        async with httpx.AsyncClient() as client:
            for attempt in range(max_attempts):
                response = await client.get(url, headers=self.headers, timeout=10.0)
                
                if response.status_code != 200:
                    raise Exception(f"Task status failed: {response.text}")
                
                data = response.json()
                status = data.get("status")
                logger.info(f"Task {task_id}: {status} ({attempt + 1}/{max_attempts})")
                
                if status in ["completed", "ready"]:
                    return data
                elif status == "failed":
                    raise Exception(f"Task failed: {data.get('error')}")
                
                await asyncio.sleep(3)
        
        raise TimeoutError(f"Task timed out after {timeout}s")
    
    async def wait_for_video_ready(self, video_id: str, timeout: int = 180) -> bool:
        """Poll until video is ready for semantic analysis"""
        max_attempts = timeout // 3
        
        for attempt in range(max_attempts):
            logger.info(f"Checking video readiness ({attempt + 1}/{max_attempts})...")
            
            try:
                if await self._verify_semantic_readiness(video_id):
                    logger.info("Video ready for analysis")
                    return True
            except Exception as e:
                # Propagate fatal errors (like unsupported index)
                raise e
            
            await asyncio.sleep(3)
        
        raise TimeoutError(f"Video not ready after {timeout}s")
    
    async def _verify_semantic_readiness(self, video_id: str) -> bool:
        """Test if video is ready for semantic queries"""
        payload = {
            "video_id": video_id,
            "prompt": "What is in this video?",
            "temperature": 0.1,
            "stream": False
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/analyze",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json=payload,
                    timeout=30.0
                )
                
                logger.info(f"Analyze response: {response.status_code} - {response.text[:200]}")
                
                if response.status_code == 200:
                    return True
                elif response.status_code == 400:
                    error = response.json()
                    code = error.get("code")
                    logger.info(f"Analyze error code: {code}")
                    if code == "video_not_ready":
                        return False
                    elif code == "index_not_supported_for_generate":
                        # Index doesn't support analyze - fatal error
                        raise Exception("Index doesn't support analyze. Create a new index with Pegasus enabled.")
                return False
            except Exception as e:
                logger.error(f"Semantic check error: {e}")
                raise
    
    # ========== ANALYSIS ==========
    
    async def analyze(self, video_id: str, prompt: str, max_retries: int = 10) -> str:
        """Run analysis with retry logic for video_not_ready"""
        url = f"{self.base_url}/analyze"
        payload = {
            "video_id": video_id,
            "prompt": prompt,
            "temperature": 0.2,
            "stream": False
        }
        
        retry_delay = 3
        
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        url,
                        headers={**self.headers, "Content-Type": "application/json"},
                        json=payload,
                        timeout=60.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("data", "")
                    
                    elif response.status_code == 400:
                        error = response.json()
                        if error.get("code") == "video_not_ready":
                            logger.info(f"Video not ready, retry {attempt + 1}/{max_retries}...")
                            await asyncio.sleep(retry_delay)
                            retry_delay = min(retry_delay * 1.5, 30)
                            continue
                        else:
                            raise Exception(f"Analysis failed: {response.text}")
                    else:
                        raise Exception(f"Analysis failed: {response.text}")
                        
                except httpx.RequestError as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Network error: {e}")
                    await asyncio.sleep(retry_delay)
        
        raise Exception(f"Analysis failed after {max_retries} attempts")
    
    async def get_object_description(self, video_id: str) -> str:
        """Get detailed scene description for 3D reconstruction"""
        prompt = """You are a 3D environment designer. Analyze this video and provide a detailed spatial description of the scene for generating a 3D model.

Describe in detail:

1. **ROOM/SPACE LAYOUT**
   - Room shape and approximate dimensions (length x width x height in meters)
   - Floor type and material (wood, tile, carpet, concrete)
   - Wall colors and materials
   - Ceiling type (flat, vaulted, exposed beams)

2. **MAJOR OBJECTS & FURNITURE**
   - List each object with position (front-left, center, back-right, etc.)
   - Approximate size of each object (width x depth x height)
   - Material and color (use hex codes like #FFFFFF)
   - Shape description (rectangular, cylindrical, organic)

3. **LIGHTING**
   - Light sources (windows, lamps, overhead lights)
   - Direction and intensity of light
   - Shadows and ambient lighting

4. **SPATIAL RELATIONSHIPS**
   - How objects relate to each other (next to, behind, on top of)
   - Distances between key objects
   - Walkable areas and blocked spaces

5. **TEXTURES & MATERIALS**
   - Surface finishes (glossy, matte, rough, smooth)
   - Patterns (striped, checkered, solid)
   - Transparency (glass, translucent materials)

Format your response so a 3D modeling AI (like Gemini) can recreate this scene using primitives (boxes, cylinders, planes) with accurate positions, scales, and materials.

Be extremely specific with measurements, positions, and colors."""
        
        return await self.analyze(video_id, prompt)
    
    async def get_view_timestamp(self, video_id: str, view: str) -> Optional[str]:
        """Get timestamp for a specific view (front, side, back, top)"""
        prompts = {
            "front": "Return the exact timestamp when the front view of the main object is best visible. Output only the timestamp in format (MM:SS)",
            "side": "Return the exact timestamp when the side view of the main object is best visible. Output only the timestamp in format (MM:SS)",
            "back": "Return the exact timestamp when the back view of the main object is best visible. Output only the timestamp in format (MM:SS)",
            "top": "Return the exact timestamp when the top view of the main object is best visible. Output only the timestamp in format (MM:SS)",
        }
        
        prompt = prompts.get(view, prompts["front"])
        
        try:
            result = await self.analyze(video_id, prompt)
            return result.strip()
        except:
            return None
    
    async def get_all_view_timestamps(self, video_id: str) -> Dict[str, Optional[str]]:
        """Get timestamps for all views"""
        views = ["front", "side", "back", "top"]
        timestamps = {}
        
        for view in views:
            logger.info(f"Getting {view} view timestamp...")
            timestamps[view] = await self.get_view_timestamp(video_id, view)
            await asyncio.sleep(0.5)  # Small delay between requests
        
        return timestamps


# ========== Singleton ==========

_api_instance = None

def get_twelve_labs_api() -> TwelveLabsAPI:
    global _api_instance
    if _api_instance is None:
        _api_instance = TwelveLabsAPI()
    return _api_instance
