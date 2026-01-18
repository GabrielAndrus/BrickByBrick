"""
Gemini 3 Pro Service for ThreeJS Generation
Takes frames + scene description from TwelveLabs and generates ThreeJS code
"""

import os
import base64
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GeminiService:
    """Gemini 3 Pro service for 3D scene generation"""
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        
        # Model priority: try Pro models first for quality, then flash for speed/quota
        # Gemini 3 Pro / Gemini 1.5 Pro for best quality
        models_to_try = [
            'gemini-1.5-pro',        # Gemini 1.5 Pro - best quality (most reliable)
            'gemini-2.0-flash',      # Fast fallback with good quality
            'gemini-1.5-flash',      # Final fallback
        ]
        
        # Try to list available models for debugging
        try:
            available_models = [m.name.split('/')[-1] for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            logger.info(f"Available Gemini models: {', '.join(available_models)}")
            
            # Check if gemini-3-pro-preview or similar exists
            pro_models = [m for m in available_models if '3' in m and 'pro' in m.lower()]
            if pro_models:
                logger.info(f"Found Gemini 3 Pro models: {pro_models}")
                # Add to front of list if found
                models_to_try = pro_models + models_to_try
        except Exception as e:
            logger.warning(f"Could not list models: {e}")
        
        self.model = None
        for model_name in models_to_try:
            try:
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Using Gemini model: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Model {model_name} not available: {e}")
        
        if self.model is None:
            raise ValueError("No Gemini models available")
    
    def _prepare_image_parts(self, frames: List[Dict[str, Any]]) -> List[Dict]:
        """Convert base64 frames to Gemini image parts"""
        image_parts = []
        
        for i, frame in enumerate(frames):
            base64_data = frame.get("image_base64", "")
            
            # Remove data URI prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]
            
            if base64_data:
                image_parts.append({
                    "mime_type": "image/jpeg",
                    "data": base64_data
                })
                logger.info(f"Added frame {i + 1} to Gemini request")
        
        return image_parts
    
    async def generate_threejs(
        self,
        frames: List[Dict[str, Any]],
        scene_description: str,
        timestamps: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate ThreeJS code from frames and scene description
        
        Args:
            frames: List of frame dicts with image_base64
            scene_description: Detailed scene description from TwelveLabs
            timestamps: Optional view timestamps
            
        Returns:
            ThreeJS JavaScript code as string
        """
        
        # Prepare the prompt
        prompt = f"""You are an expert ThreeJS developer. Based on the provided images and scene description, generate a complete, working ThreeJS scene that accurately recreates the environment.

## SCENE DESCRIPTION FROM VIDEO ANALYSIS:
{scene_description}

## VIEW TIMESTAMPS:
{timestamps if timestamps else "Not available"}

## YOUR TASK:
Generate a complete, self-contained ThreeJS scene that:

1. **Recreates the room/environment** with accurate:
   - Dimensions (use the measurements from the description)
   - Wall, floor, and ceiling geometry
   - Colors and materials (use the hex codes provided)

2. **Places all objects/furniture** with:
   - Correct positions (x, y, z coordinates)
   - Accurate sizes and proportions
   - Appropriate materials (color, roughness, metalness)
   - Correct shapes (use BoxGeometry, CylinderGeometry, SphereGeometry, etc.)

3. **Sets up proper lighting** with:
   - Ambient light for base illumination
   - Directional/point lights matching the scene
   - Shadows if appropriate

4. **Includes camera and controls**:
   - OrbitControls for navigation
   - Good initial camera position to view the scene

## OUTPUT FORMAT:
Return ONLY valid JavaScript code that can be executed directly. The code should:
- Create a complete ThreeJS scene
- Include all necessary setup (renderer, scene, camera)
- Add OrbitControls
- Include an animation loop
- Be wrapped in a function called `createScene(container)` that takes a DOM element

Start your response with the code immediately (no markdown code blocks, no explanations before the code).
"""

        try:
            # Prepare image parts
            image_parts = self._prepare_image_parts(frames)
            
            # Build the content array
            content = []
            
            # Add images first
            for img_part in image_parts:
                content.append(img_part)
            
            # Add the text prompt
            content.append(prompt)
            
            logger.info(f"Sending {len(image_parts)} images + prompt to Gemini")
            
            # Generate response
            response = self.model.generate_content(
                content,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 32000,
                }
            )
            
            # Extract the code
            code = response.text
            
            # Clean up the response - remove markdown code blocks if present
            if code.startswith("```javascript"):
                code = code[len("```javascript"):].strip()
            elif code.startswith("```js"):
                code = code[len("```js"):].strip()
            elif code.startswith("```"):
                code = code[3:].strip()
            
            if code.endswith("```"):
                code = code[:-3].strip()
            
            logger.info(f"Generated ThreeJS code: {len(code)} characters")
            
            return code
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise Exception(f"Failed to generate ThreeJS: {e}")
    
    async def generate_threejs_from_video(
        self,
        video_path: str,
        scene_description: Optional[str] = None
    ) -> str:
        """
        Generate ThreeJS code directly from video file
        
        Args:
            video_path: Path to video file
            scene_description: Optional detailed description from TwelveLabs
            
        Returns:
            ThreeJS JavaScript code as string
        """
        
        prompt = f"""You are an expert Creative Developer and 3D Spatial Analyst specialized in Three.js.
Your goal is to "transcode" the attached video into a procedural Three.js scene.

{f"## SCENE DESCRIPTION FROM VIDEO ANALYSIS:\n{scene_description}\n" if scene_description else ""}

## INPUT PROCESSING
1. **Analyze the Video Layout:**
   - Identify the "Anchor Object" (e.g., the main desk, a central pillar, or a specific wall).
   - Establish a mental grid: Where are other objects relative to this anchor?
   - Detect the dominant colors (hex codes) and material types (wood, metal, plastic, glass).
   - Identify light sources (window direction, ceiling lights).

2. **Geometry Strategy:**
   - Do NOT just create random boxes.
   - Use "Composite Primitives": Build complex objects (like a chair) using a THREE.Group() containing multiple simple geometries (e.g., legs = cylinders, seat = box).
   - Create helper functions for repeated objects (e.g., `function createOfficeChair(x, z)`).

## OUTPUT SPECIFICATIONS
Return ONLY valid JavaScript code containing the `createScene` function.

### Code Requirements:
1. **Container & Boilerplate:**
   - Must use `container.appendChild(renderer.domElement)`.
   - Must include a `ResizeObserver` or window resize handler to keep the canvas responsive.
   - Must include `OrbitControls`.

2. **Visual Fidelity:**
   - **Lighting:** Do not rely solely on AmbientLight. Use `DirectionalLight` with shadows enabled (`castShadow = true`) to mimic the video's main light source.
   - **Materials:** Use `MeshStandardMaterial`. Adjust `roughness` and `metalness` to match the video surfaces (e.g., glossy whiteboard vs. matte carpet).

3. **Scene Population:**
   - Recreate the floor plan seen in the video.
   - Place furniture groups at their estimated relative positions.

### FORMAT
RETURN ONLY THE JAVASCRIPT CODE. NO MARKDOWN BACKTICKS. NO TEXT.

function createScene(container) {{
    // 1. Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(/* EXTRACTED_FROM_VIDEO_WALL_COLOR */);
    
    // ... camera, renderer, controls setup ...

    // 2. Asset Generators (factories for repeated items found in video)
    function createChair(x, z, rotation) {{
        const group = new THREE.Group();
        // ... build chair from primitives ...
        group.position.set(x, 0, z);
        group.rotation.y = rotation;
        scene.add(group);
    }}

    // 3. Scene Composition
    // ... logic to place objects based on video analysis ...

    // 4. Lighting
    // ... lighting setup matching video mood ...

    // 5. Animation Loop
    function animate() {{
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }}
    animate();

    return {{ scene, camera, renderer, controls }};
}}
"""
        
        try:
            # Upload video file to Gemini
            logger.info(f"Uploading video to Gemini: {video_path}")
            video_file = genai.upload_file(path=video_path)
            logger.info(f"Video uploaded: {video_file.uri}, state: {video_file.state}")
            
            # Wait for file to be ACTIVE (required before using in generate_content)
            max_wait_time = 120  # 2 minutes max
            wait_interval = 2  # Check every 2 seconds
            elapsed = 0
            
            # Check current state - handle both string and enum-like state
            current_state = str(video_file.state).upper() if hasattr(video_file.state, '__str__') else str(video_file.state)
            if hasattr(video_file.state, 'name'):
                current_state = str(video_file.state.name).upper()
            
            logger.info(f"Initial file state: {current_state}")
            
            while "ACTIVE" not in current_state:
                if elapsed >= max_wait_time:
                    raise Exception(f"Video file did not become ACTIVE within {max_wait_time} seconds (final state: {current_state})")
                
                logger.info(f"Waiting for file to be ACTIVE... current state: {current_state} ({elapsed}s)")
                await asyncio.sleep(wait_interval)  # Use asyncio.sleep for async function
                elapsed += wait_interval
                
                # Refresh file state
                video_file = genai.get_file(video_file.name)
                current_state = str(video_file.state).upper() if hasattr(video_file.state, '__str__') else str(video_file.state)
                if hasattr(video_file.state, 'name'):
                    current_state = str(video_file.state.name).upper()
            
            logger.info(f"Video file is now ACTIVE (waited {elapsed}s)")
            
            # Build content with video
            content = [video_file]
            if scene_description:
                content.append(f"Additional context: {scene_description}")
            content.append(prompt)
            
            logger.info("Sending video + prompt to Gemini for ThreeJS generation")
            
            # Generate response
            response = self.model.generate_content(
                content,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 32000,
                }
            )
            
            # Extract and clean the code
            code = response.text
            
            # Clean up markdown code blocks
            if code.startswith("```javascript"):
                code = code[len("```javascript"):].strip()
            elif code.startswith("```js"):
                code = code[len("```js"):].strip()
            elif code.startswith("```"):
                code = code[3:].strip()
            
            if code.endswith("```"):
                code = code[:-3].strip()
            
            logger.info(f"Generated ThreeJS code from video: {len(code)} characters")
            
            # Clean up uploaded file
            try:
                genai.delete_file(video_file.name)
                logger.info("Cleaned up uploaded video file")
            except Exception as e:
                logger.warning(f"Failed to delete uploaded file: {e}")
            
            return code
            
        except Exception as e:
            logger.error(f"Gemini video error: {e}")
            raise Exception(f"Failed to generate ThreeJS from video: {e}")
    
    async def generate_threejs_simple(self, scene_description: str) -> str:
        """Generate ThreeJS from description only (no images)"""
        
        prompt = f"""You are an expert ThreeJS developer. Generate a complete ThreeJS scene based on this description:

{scene_description}

Generate a complete, self-contained ThreeJS scene with:
1. Room geometry (walls, floor, ceiling)
2. All furniture/objects mentioned
3. Proper lighting
4. OrbitControls for navigation

Return ONLY valid JavaScript code wrapped in a function called `createScene(container)`.
No markdown, no explanations - just the code."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 32000,
                }
            )
            
            code = response.text
            
            # Clean up markdown
            if "```" in code:
                lines = code.split("\n")
                clean_lines = []
                in_code = False
                for line in lines:
                    if line.startswith("```"):
                        in_code = not in_code
                        continue
                    if in_code or not line.startswith("```"):
                        clean_lines.append(line)
                code = "\n".join(clean_lines)
            
            return code.strip()
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise Exception(f"Failed to generate ThreeJS: {e}")


# Singleton
_gemini_service = None

def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
