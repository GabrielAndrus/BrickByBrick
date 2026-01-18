"""
TwelveLabs Visual Intelligence Service
Based on working pipeline implementation
"""

import httpx
import asyncio
import os
import re
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
        """Get extremely detailed scene description for 3D reconstruction using Pegasus"""
        prompt = """You are an expert 3D environment designer analyzing a video. Your task is to provide a comprehensive, detailed description of the scene to enable accurate 3D reconstruction.

Please describe what you can observe in the following structure:

1. **ROOM/SPACE LAYOUT**
   - Room dimensions (estimated): length x width x height in meters if visible
   - Floor: material type (wood, tile, carpet, etc.), color description, texture
   - Walls: describe each wall - color, material if visible, any decorations, windows, or features
   - Ceiling: type (flat, vaulted, etc.), color, any fixtures or features

2. **OBJECTS & FURNITURE**
   For each visible object, please describe:
   - Name/Type: what the object is (e.g., "desk", "chair", "lamp")
   - Position: where it is located in the room (relative to walls or other objects)
   - Size: approximate dimensions if you can estimate
   - Shape: basic geometry (rectangular, cylindrical, etc.)
   - Color: color description or hex code if identifiable
   - Material: what it appears to be made of (wood, metal, fabric, etc.)
   - Texture: surface appearance (smooth, rough, glossy, matte)
   - Additional details: any notable features

3. **LIGHTING**
   - Light sources: describe visible lights (windows, lamps, overhead lights)
   - Light direction: where light is coming from
   - Brightness: overall lighting level of the room

4. **SPATIAL RELATIONSHIPS**
   - Object positions: describe where objects are relative to each other
   - Distances: approximate spacing between key objects if visible
   - Layout: describe the overall arrangement of furniture and objects

5. **TEXTURES & MATERIALS**
   - Surface finishes: describe visible textures and finishes
   - Materials: what surfaces appear to be made of
   - Patterns: any visible patterns (flooring patterns, fabric patterns, etc.)

6. **ADDITIONAL DETAILS**
   - Decorative elements: artwork, plants, rugs, etc.
   - Functional elements: windows, doors, outlets if visible
   - Color scheme: dominant colors in the scene
   - Style: overall aesthetic or style

Please include:
- Estimates or descriptions of sizes and dimensions where possible
- Color descriptions (specific colors or hex codes if you can identify them)
- Descriptions of all visible objects and furniture
- Spatial relationships between objects (what's near what, positions relative to walls)
- Materials and textures you can observe
- Lighting information

Be as detailed and specific as you can while staying accurate to what's actually visible in the video."""
        
        return await self.analyze(video_id, prompt)
    
    async def identify_room_parts(self, video_id: str) -> Dict[str, str]:
        """Ask Marengo to identify and name the different sides/parts of the room visible in the video"""
        prompt = """Analyze the video and identify the different sides, walls, and areas of the room that are visible. 
For each distinct part (like a wall, corner, or area), describe it briefly.
Output a simple list format like: "north wall", "east wall", "floor", "ceiling", "corner", etc.
If the room doesn't have clear directional walls, use descriptive names like "wall_with_window", "back_wall", "side_area", etc.
Only list parts that are clearly visible in the video. Keep it to 6-8 key parts maximum.
Output format: Just list the part names, one per line."""
        
        try:
            result = await self.analyze(video_id, prompt)
            # Parse the response to extract room part names
            parts = []
            for line in result.strip().split('\n'):
                line = line.strip()
                # Remove numbering, bullets, dashes
                line = re.sub(r'^[-\d\.\s]+', '', line)
                line = line.strip()
                if line and len(line) < 50:  # Reasonable part name length
                    # Normalize: convert to lowercase and replace spaces with underscores
                    normalized = line.lower().replace(' ', '_').replace('-', '_')
                    parts.append(normalized)
            
            logger.info(f"Marengo identified room parts: {parts}")
            return {part: part for part in parts[:8]}  # Limit to 8 parts
        except Exception as e:
            logger.warning(f"Failed to identify room parts: {e}")
            # Fallback to standard parts
            return {
                "right_side": "right_side",
                "left_side": "left_side", 
                "floor": "floor",
                "ceiling": "ceiling",
                "back_wall": "back_wall",
                "center": "center"
            }
    
    async def get_room_part_timestamp(self, video_id: str, part_name: str, part_description: str = None) -> Optional[str]:
        """Get timestamp for a specific room part using Marengo"""
        if part_description is None:
            part_description = part_name.replace('_', ' ')
        
        # More specific prompt to get accurate timestamps for distinct room parts
        prompt = f"""Find the exact moment in the video when '{part_description}' is most clearly visible and well-framed.
This should be a distinct view that shows this specific part of the room from a good angle.
Return ONLY the timestamp in MM:SS format (e.g., "00:15" or "1:30").
If the part is not clearly visible, return "none"."""
        
        try:
            result = await self.analyze(video_id, prompt)
            result = result.strip().lower()
            
            # Handle "none" or empty responses
            if not result or "none" in result or "not visible" in result or "not found" in result:
                return None
            
            # Extract timestamp - handle MM:SS format
            match = re.search(r'(\d{1,2}):(\d{2})', result)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                # Validate reasonable timestamp (less than 2 hours)
                if minutes < 120 and seconds < 60:
                    return match.group(0)
            
            # Try to parse as just seconds if no colon found
            match_seconds = re.search(r'^(\d+\.?\d*)\s*(?:s|seconds?)?$', result)
            if match_seconds:
                total_sec = float(match_seconds.group(1))
                mins = int(total_sec // 60)
                secs = int(total_sec % 60)
                if total_sec < 7200:  # Less than 2 hours
                    return f"{mins}:{secs:02d}"
            
            logger.warning(f"Could not parse timestamp for {part_name}: {result}")
            return None
        except Exception as e:
            logger.warning(f"Failed to get timestamp for {part_name}: {e}")
            return None
    
    async def get_all_room_timestamps(self, video_id: str, parts: Optional[list] = None) -> Dict[str, Optional[str]]:
        """Get timestamps for specific parts of the room using Marengo"""
        # Default parts to extract if not specified
        if parts is None:
            parts = [
                "right_side",
                "left_side", 
                "floor",
                "ceiling",
                "back_wall",
                "front_area",
                "corner",
                "center"
            ]
        
        # Part descriptions for better Marengo understanding
        part_descriptions = {
            "right_side": "the right side of the room",
            "left_side": "the left side of the room",
            "floor": "the floor of the room",
            "ceiling": "the ceiling of the room",
            "back_wall": "the back wall of the room",
            "front_area": "the front area of the room",
            "corner": "a corner of the room",
            "center": "the center of the room",
            "wall_with_window": "a wall with a window",
            "entrance": "the entrance or doorway",
            "side_wall": "a side wall",
            "window": "a window in the room"
        }
        
        # Get timestamps for each requested part
        timestamps = {}
        for part in parts:
            description = part_descriptions.get(part, part.replace('_', ' '))
            logger.info(f"Getting timestamp for: {part} ({description})...")
            timestamps[part] = await self.get_room_part_timestamp(video_id, part, description)
            await asyncio.sleep(0.5)  # Small delay between requests
        
        return timestamps
    
    # Keep old methods for backwards compatibility
    async def get_view_timestamp(self, video_id: str, view: str) -> Optional[str]:
        """Get timestamp for a specific view (front, side, back, top) - DEPRECATED: use get_room_part_timestamp"""
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
        """Get timestamps for all views - DEPRECATED: use get_all_room_timestamps"""
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