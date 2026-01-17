import os
import time
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from twelvelabs import TwelveLabs
from twelvelabs.errors import RateLimitError, NotFoundError, APIError
from twelvelabs.types.task import TaskStatus

from app.models.schemas import ObjectAnalysisResponse

logger = logging.getLogger(__name__)


class TwelveLabsService:
    """
    Service for interacting with TwelveLabs API for video intelligence.
    Handles video indexing, analysis, and structured extraction.
    """
    
    def __init__(self):
        """Initialize the TwelveLabs client using API key from environment."""
        api_key = os.getenv("TWELVE_LABS_API_KEY")
        if not api_key:
            raise ValueError("TWELVE_LABS_API_KEY environment variable is required")
        self.client = TwelveLabs(api_key=api_key)
        self._index_id: Optional[str] = None
    
    def ensure_index_exists(self, index_name: str = "lego-assembly-index") -> str:
        """
        Ensure a video index exists with required engines configured.
        
        Args:
            index_name: Name of the index to create or use
            
        Returns:
            Index ID string
            
        Raises:
            RuntimeError: If index creation or configuration fails
        """
        try:
            # List existing indexes
            indexes = self.client.index.list()
            
            # Check if index already exists
            for index in indexes:
                if index.name == index_name:
                    logger.info(f"Using existing index: {index.id} ({index.name})")
                    self._index_id = index.id
                    return index.id
            
            # Create new index if it doesn't exist
            logger.info(f"Creating new index: {index_name}")
            index = self.client.index.create(
                index_name=index_name,
                engines=[
                    {
                        "engine_name": "marengo3.0",
                        "engine_options": ["visual", "audio"]
                    },
                    {
                        "engine_name": "pegasus1.2",
                        "engine_options": ["visual", "audio"]
                    }
                ]
            )
            self._index_id = index.id
            logger.info(f"Created index: {index.id}")
            return index.id
            
        except RateLimitError as e:
            logger.error("Rate limit exceeded while managing index")
            raise RuntimeError("Rate limit exceeded while managing index") from e
        except APIError as e:
            logger.error(f"API error while managing index: {str(e)}")
            raise RuntimeError(f"Failed to manage index: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error while managing index: {str(e)}")
            raise RuntimeError(f"Unexpected error while managing index: {str(e)}") from e
    
    def upload_and_index(
        self,
        video_path: str,
        index_id: Optional[str] = None,
        status_callback: Optional[callable] = None
    ) -> str:
        """
        Upload a video file and wait for indexing to complete.
        
        Args:
            video_path: Path to the local video file
            index_id: Index ID to use (uses cached index_id if None)
            status_callback: Optional callback function(status, progress) for status updates
            
        Returns:
            video_id: The ID of the indexed video
            
        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If upload or indexing fails
        """
        # Ensure index exists
        if index_id is None:
            if self._index_id is None:
                self.ensure_index_exists()
            index_id = self._index_id
        
        if index_id is None:
            raise RuntimeError("No index ID available")
        
        # Validate video file exists
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        try:
            # Create upload task
            logger.info(f"Uploading video: {video_path}")
            # Try both task and tasks (SDK might use either)
            try:
                task = self.client.tasks.create(
                    index_id=index_id,
                    file_path=str(video_file.absolute())
                )
            except AttributeError:
                # Fallback to singular if SDK uses singular
                task = self.client.task.create(
                    index_id=index_id,
                    file_path=str(video_file.absolute())
                )
            
            if status_callback:
                status_callback("uploading", 0)
            
            # Wait for task to complete with callback
            def progress_callback(status: TaskStatus):
                """Internal callback to log and forward status updates"""
                progress = getattr(status, 'progress', 0) if hasattr(status, 'progress') else None
                status_str = getattr(status, 'status', 'unknown')
                logger.info(f"Task status: {status_str}, Progress: {progress}%")
                
                if status_callback:
                    status_callback(status_str, progress)
            
            # Wait for task completion
            task.wait_for_done(callback=progress_callback)
            
            # Check final status
            if task.status != "ready":
                error_msg = f"Task failed with status: {task.status}"
                if hasattr(task, 'error'):
                    error_msg += f", Error: {task.error}"
                raise RuntimeError(error_msg)
            
            video_id = task.video_id
            logger.info(f"Video indexed successfully: {video_id}")
            return video_id
            
        except RateLimitError as e:
            logger.error("Rate limit exceeded during video upload/indexing")
            raise RuntimeError("Rate limit exceeded during video upload/indexing") from e
        except APIError as e:
            logger.error(f"API error during video upload/indexing: {str(e)}")
            raise RuntimeError(f"Failed to upload/index video: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during video upload/indexing: {str(e)}")
            raise RuntimeError(f"Unexpected error during video upload/indexing: {str(e)}") from e
    
    def analyze_object(
        self,
        video_id: str,
        index_id: Optional[str] = None
    ) -> ObjectAnalysisResponse:
        """
        Analyze an object in a video using Pegasus 1.2 engine with structured JSON output.
        
        Args:
            video_id: ID of the video to analyze
            index_id: Index ID (optional, uses cached if None)
            
        Returns:
            ObjectAnalysisResponse with dimensions, colors, and complexity
            
        Raises:
            RuntimeError: If analysis fails or rate limit exceeded
        """
        if index_id is None:
            if self._index_id is None:
                self.ensure_index_exists()
            index_id = self._index_id
        
        if index_id is None:
            raise RuntimeError("No index ID available")
        
        # Define JSON schema for structured response with Three.js mesh
        json_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "dimensions_mm": {
                    "type": "object",
                    "properties": {
                        "height": {"type": "number"},
                        "width": {"type": "number"},
                        "depth": {"type": "number"}
                    },
                    "required": ["height", "width", "depth"]
                },
                "dominant_colors": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": "^#[0-9A-Fa-f]{6}$"
                    }
                },
                "complexity": {
                    "type": "object",
                    "properties": {
                        "is_airy": {"type": "boolean"},
                        "has_curves": {"type": "boolean"},
                        "has_floating_parts": {"type": "boolean"}
                    },
                    "required": ["is_airy", "has_curves", "has_floating_parts"]
                },
                "threejs_mesh": {
                    "type": "object",
                    "properties": {
                        "vertices": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3
                            },
                            "description": "List of vertex positions [x, y, z] in millimeters"
                        },
                        "faces": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 3,
                                "maxItems": 3
                            },
                            "description": "List of triangular faces as vertex indices [i, j, k]"
                        },
                        "normals": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3
                            },
                            "description": "Optional vertex normals [nx, ny, nz]"
                        },
                        "colors": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "pattern": "^#[0-9A-Fa-f]{6}$"
                            },
                            "description": "Optional vertex colors (hex codes)"
                        }
                    },
                    "required": ["vertices", "faces"]
                }
            },
            "required": ["dimensions_mm", "dominant_colors", "complexity", "threejs_mesh"]
        }
        
        prompt = (
            "Analyze this object and provide a complete Three.js-compatible mesh representation. "
            "Estimate the real-world scale in millimeters and create a 3D mesh model.\n\n"
            "Requirements:\n"
            "1. Extract dimensions: height, width, depth in millimeters\n"
            "2. Identify dominant colors as hex codes\n"
            "3. Assess complexity: airiness, curviness, floating parts\n"
            "4. **CRITICAL**: Generate a Three.js-compatible JSON mesh with:\n"
            "   - vertices: Array of [x, y, z] coordinates in millimeters\n"
            "   - faces: Array of [i, j, k] triangular face indices (referencing vertex indices)\n"
            "   - normals: Optional vertex normals [nx, ny, nz] for proper lighting\n"
            "   - colors: Optional vertex colors (hex codes) matching dominant_colors\n\n"
            "The mesh should accurately represent the object's 3D geometry as seen in the video. "
            "Use triangular faces only. Ensure vertices form a closed, watertight mesh suitable "
            "for voxelization and LEGO brick conversion."
        )
        
        try:
            logger.info(f"Analyzing video {video_id} with Pegasus 1.2 engine")
            response = self.client.analyze(
                video_id=video_id,
                index_id=index_id,
                engine_name="pegasus1.2",
                prompt=prompt,
                response_format={
                    "type": "json_schema",
                    "json_schema": json_schema
                }
            )
            
            # Parse and validate response
            if not hasattr(response, 'data') or not response.data:
                raise RuntimeError("Empty response from analysis")
            
            # Parse JSON string to dict if needed
            if isinstance(response.data, str):
                data = json.loads(response.data)
            else:
                data = response.data
            
            # Validate and create Pydantic model
            return ObjectAnalysisResponse(**data)
            
        except RateLimitError as e:
            logger.warning("Rate limit exceeded, retrying with exponential backoff...")
            # Retry with exponential backoff
            wait_time = 1
            max_retries = 3
            for attempt in range(max_retries):
                time.sleep(wait_time)
                try:
                    response = self.client.analyze(
                        video_id=video_id,
                        index_id=index_id,
                        engine_name="pegasus1.2",
                        prompt=prompt,
                        response_format={
                            "type": "json_schema",
                            "json_schema": json_schema
                        }
                    )
                    
                    if isinstance(response.data, str):
                        data = json.loads(response.data)
                    else:
                        data = response.data
                    
                    return ObjectAnalysisResponse(**data)
                    
                except RateLimitError:
                    wait_time *= 2
                    if attempt == max_retries - 1:
                        raise RuntimeError("Rate limit exceeded after retries") from e
                        
        except NotFoundError as e:
            logger.error(f"Video ID {video_id} not found or not indexed")
            raise RuntimeError(f"Video ID {video_id} not found or not indexed") from e
        except APIError as e:
            logger.error(f"API error during analysis: {str(e)}")
            raise RuntimeError(f"Analysis failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {str(e)}")
            raise RuntimeError(f"Analysis failed: {str(e)}") from e
