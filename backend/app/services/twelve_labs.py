import os
import time
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from twelvelabs import TwelveLabs
from twelvelabs.errors import TooManyRequestsError, NotFoundError, BadRequestError

from app.models.schemas import ObjectAnalysisResponse, SceneryAnalysisResponse

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
            indexes = self.client.indexes.list()
            
            # Check if index already exists
            for index in indexes:
                if index.index_name == index_name:
                    logger.info(f"Using existing index: {index.id} ({index.index_name})")
                    self._index_id = index.id
                    return index.id
            
            # Create new index if it doesn't exist
            logger.info(f"Creating new index: {index_name}")
            index = self.client.indexes.create(
                index_name=index_name,
                models=[
                    {
                        "model_name": "marengo2.7",
                        "model_options": ["visual", "audio"]
                    },
                    {
                        "model_name": "pegasus1.2",
                        "model_options": ["visual", "audio"]
                    }
                ]
            )
            self._index_id = index.id
            logger.info(f"Created index: {index.id}")
            return index.id
            
        except TooManyRequestsError as e:
            logger.error("Rate limit exceeded while managing index")
            raise RuntimeError("Rate limit exceeded while managing index") from e
        except BadRequestError as e:
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
        
        # Check file size
        file_size = video_file.stat().st_size
        logger.info(f"Video file size: {file_size} bytes")
        
        if file_size == 0:
            raise RuntimeError("Video file is empty (0 bytes)")
        
        if file_size < 1000:
            raise RuntimeError(f"Video file is too small ({file_size} bytes) - likely corrupted or invalid")
        
        try:
            # Create upload task
            logger.info(f"Uploading video: {video_path}")
            
            if status_callback:
                status_callback("uploading", 0)
            
            # Read file and pass as bytes with filename
            with open(video_file, "rb") as f:
                file_content = f.read()
            
            logger.info(f"Read {len(file_content)} bytes from {video_path}")
            
            if len(file_content) == 0:
                raise RuntimeError("Failed to read video file - content is empty")
            
            # Create task with video file content
            task = self.client.tasks.create(
                index_id=index_id,
                video_file=(video_file.name, file_content)
            )
            
            logger.info(f"Task created: {task.id}")
            
            if status_callback:
                status_callback("indexing", 25)
            
            # Wait for task completion using the SDK's wait method
            task_result = self.client.tasks.wait_for_done(
                task_id=task.id,
                sleep_interval=5
            )
            
            # Check final status
            if task_result.status != "ready":
                error_msg = f"Task failed with status: {task_result.status}"
                raise RuntimeError(error_msg)
            
            video_id = task_result.video_id
            logger.info(f"Video indexed successfully: {video_id}")
            
            if status_callback:
                status_callback("complete", 100)
            
            return video_id
            
        except TooManyRequestsError as e:
            logger.error("Rate limit exceeded during video upload/indexing")
            raise RuntimeError("Rate limit exceeded during video upload/indexing") from e
        except BadRequestError as e:
            logger.error(f"API error during video upload/indexing: {str(e)}")
            raise RuntimeError(f"Failed to upload/index video: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during video upload/indexing: {str(e)}")
            raise RuntimeError(f"Unexpected error during video upload/indexing: {str(e)}") from e
    
    def analyze_object(
        self,
        video_id: str,
        object_id: str = "object_v1"
    ) -> ObjectAnalysisResponse:
        """
        Analyze an object in a video with structured JSON output for LEGO reconstruction.
        
        Args:
            video_id: ID of the video to analyze
            object_id: Identifier for the object being analyzed
            
        Returns:
            ObjectAnalysisResponse with voxel cloud, dimensions, and structural metadata
            
        Raises:
            RuntimeError: If analysis fails or rate limit exceeded
        """
        # Define JSON schema for structured response
        json_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "object_id": {"type": "string"},
                "raw_vision_data": {
                    "type": "object",
                    "properties": {
                        "estimated_dimensions_mm": {
                            "type": "object",
                            "properties": {
                                "h": {"type": "number"},
                                "w": {"type": "number"},
                                "d": {"type": "number"}
                            },
                            "required": ["h", "w", "d"]
                        },
                        "voxel_cloud": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "point": {
                                        "type": "array",
                                        "items": {"type": "integer"}
                                    },
                                    "color_hex": {"type": "string"}
                                },
                                "required": ["point", "color_hex"]
                            }
                        },
                        "confidence_score": {"type": "number"}
                    },
                    "required": ["estimated_dimensions_mm", "voxel_cloud", "confidence_score"]
                },
                "structural_metadata": {
                    "type": "object",
                    "properties": {
                        "is_airy": {"type": "boolean"},
                        "has_curves": {"type": "boolean"},
                        "missing_surfaces": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["is_airy", "has_curves", "missing_surfaces"]
                }
            },
            "required": ["object_id", "raw_vision_data", "structural_metadata"]
        }
        
        prompt = f"""Analyze the object in this video for LEGO brick reconstruction. Return a JSON object with:

1. object_id: Use "{object_id}"

2. raw_vision_data:
   - estimated_dimensions_mm: Real-world dimensions in millimeters (h=height, w=width, d=depth)
   - voxel_cloud: Array of voxel points representing the object's 3D shape. Each point has:
     - point: [x, y, z] coordinates (integers, where each unit = ~8mm LEGO stud)
     - color_hex: Dominant color at that point as hex code (e.g., "#CC0000")
   - confidence_score: Your confidence in the analysis (0.0 to 1.0)

3. structural_metadata:
   - is_airy: true if object has sparse/open structures with gaps
   - has_curves: true if object has curved surfaces
   - missing_surfaces: List of surfaces that couldn't be analyzed (e.g., "bottom", "rear_left")

Generate at least 10-20 voxel points to capture the object's shape. Return ONLY valid JSON."""
        
        try:
            logger.info(f"Analyzing object in video {video_id}")
            response = self.client.analyze(
                video_id=video_id,
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
            
            logger.info(f"Raw TwelveLabs response: {json.dumps(data, indent=2)}")
            
            # Handle case where TwelveLabs returns old format or different structure
            # Transform to our expected schema if needed
            if 'raw_vision_data' not in data:
                logger.warning("TwelveLabs returned unexpected format, transforming...")
                # Try to extract from old format or create default structure
                dims = data.get('dimensions_mm', data.get('estimated_dimensions_mm', {}))
                colors = data.get('dominant_colors', [])
                complexity = data.get('complexity', {})
                
                # Build voxel cloud from colors if not present
                voxel_cloud = []
                for i, color in enumerate(colors[:20] if colors else ['#808080']):
                    voxel_cloud.append({
                        "point": [i % 5, i // 5, 0],
                        "color_hex": color if color.startswith('#') else f"#{color}"
                    })
                
                data = {
                    "object_id": object_id,
                    "raw_vision_data": {
                        "estimated_dimensions_mm": {
                            "h": dims.get('h', dims.get('height', 50)),
                            "w": dims.get('w', dims.get('width', 50)),
                            "d": dims.get('d', dims.get('depth', 50))
                        },
                        "voxel_cloud": voxel_cloud,
                        "confidence_score": data.get('confidence_score', 0.7)
                    },
                    "structural_metadata": {
                        "is_airy": complexity.get('is_airy', False),
                        "has_curves": complexity.get('has_curves', False),
                        "missing_surfaces": complexity.get('missing_surfaces', data.get('missing_surfaces', []))
                    }
                }
                logger.info(f"Transformed data: {json.dumps(data, indent=2)}")
            
            logger.info(f"Object analysis complete: {len(data.get('raw_vision_data', {}).get('voxel_cloud', []))} voxels")
            
            # Validate and create Pydantic model
            try:
                return ObjectAnalysisResponse(**data)
            except Exception as validation_error:
                logger.error(f"Pydantic validation failed: {validation_error}")
                logger.error(f"Data that failed validation: {json.dumps(data, indent=2)}")
                raise RuntimeError(f"Response validation failed: {validation_error}")
            
        except TooManyRequestsError as e:
            logger.warning("Rate limit exceeded, retrying with exponential backoff...")
            wait_time = 1
            max_retries = 3
            for attempt in range(max_retries):
                time.sleep(wait_time)
                try:
                    response = self.client.analyze(
                        video_id=video_id,
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
                    
                except TooManyRequestsError:
                    wait_time *= 2
                    if attempt == max_retries - 1:
                        raise RuntimeError("Rate limit exceeded after retries") from e
                        
        except NotFoundError as e:
            logger.error(f"Video ID {video_id} not found or not indexed")
            raise RuntimeError(f"Video ID {video_id} not found or not indexed") from e
        except BadRequestError as e:
            logger.error(f"API error during analysis: {str(e)}")
            raise RuntimeError(f"Analysis failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {str(e)}")
            raise RuntimeError(f"Analysis failed: {str(e)}") from e

    def analyze_scenery(
        self,
        video_id: str,
        session_id: str = "session_01",
        theme: str = "urban_park"
    ) -> SceneryAnalysisResponse:
        """
        Analyze a scenery/environment video for LEGO world building.
        
        Args:
            video_id: ID of the video to analyze
            session_id: Identifier for this analysis session
            theme: Theme hint for the scenery (e.g., "urban_park", "city", "nature")
            
        Returns:
            SceneryAnalysisResponse with world metadata, brick layers, and anchors
            
        Raises:
            RuntimeError: If analysis fails or rate limit exceeded
        """
        json_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "world_metadata": {
                    "type": "object",
                    "properties": {
                        "grid_unit": {"type": "string"},
                        "total_dimensions": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "z": {"type": "integer"}
                            },
                            "required": ["x", "y", "z"]
                        },
                        "theme": {"type": "string"}
                    },
                    "required": ["grid_unit", "total_dimensions", "theme"]
                },
                "scenery_layers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "layer_id": {"type": "string"},
                            "bricks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "part_id": {"type": "string"},
                                        "color_id": {"type": "integer"},
                                        "pos": {
                                            "type": "array",
                                            "items": {"type": "integer"}
                                        },
                                        "type": {"type": "string"}
                                    },
                                    "required": ["part_id", "color_id", "pos", "type"]
                                }
                            }
                        },
                        "required": ["layer_id", "bricks"]
                    }
                },
                "anchors": {
                    "type": "object",
                    "properties": {
                        "road_center": {
                            "type": "array",
                            "items": {"type": "integer"}
                        },
                        "flat_surface_zones": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "integer"}
                            }
                        }
                    },
                    "required": ["road_center", "flat_surface_zones"]
                }
            },
            "required": ["session_id", "world_metadata", "scenery_layers", "anchors"]
        }
        
        prompt = f"""Analyze this scenery/environment video for LEGO world building. Return a JSON object with:

1. session_id: Use "{session_id}"

2. world_metadata:
   - grid_unit: "1x1_plate" (standard LEGO unit)
   - total_dimensions: Estimated world size in grid units (x, y, z)
   - theme: Use "{theme}" or suggest a more appropriate theme

3. scenery_layers: Array of layers from bottom to top. Each layer has:
   - layer_id: e.g., "baseplate_0", "ground_1", "structures_2"
   - bricks: Array of brick placements with:
     - part_id: LEGO part number (e.g., "3811" for baseplate, "3001" for 2x4 brick)
     - color_id: LEGO color ID (2=green, 6=tan, 1=white, etc.)
     - pos: [x, y, z] position in grid
     - type: Descriptive type (e.g., "foundation", "grass_patch", "path", "wall")

4. anchors: Key positions for object placement
   - road_center: [x, y, z] center of any road/path
   - flat_surface_zones: Array of [x, y, z] positions suitable for placing objects

Create at least 2-3 layers with 5-10 bricks each. Return ONLY valid JSON."""
        
        try:
            logger.info(f"Analyzing scenery in video {video_id}")
            response = self.client.analyze(
                video_id=video_id,
                prompt=prompt,
                response_format={
                    "type": "json_schema",
                    "json_schema": json_schema
                }
            )
            
            if not hasattr(response, 'data') or not response.data:
                raise RuntimeError("Empty response from analysis")
            
            if isinstance(response.data, str):
                data = json.loads(response.data)
            else:
                data = response.data
            
            logger.info(f"Scenery analysis complete: {len(data.get('scenery_layers', []))} layers")
            
            return SceneryAnalysisResponse(**data)
            
        except NotFoundError as e:
            logger.error(f"Video ID {video_id} not found or not indexed")
            raise RuntimeError(f"Video ID {video_id} not found or not indexed") from e
        except BadRequestError as e:
            logger.error(f"API error during scenery analysis: {str(e)}")
            raise RuntimeError(f"Scenery analysis failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during scenery analysis: {str(e)}")
            raise RuntimeError(f"Scenery analysis failed: {str(e)}") from e
