import subprocess
import os
import base64
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FFmpegProcessor:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
    
    def extract_frames(
        self, 
        video_path: str, 
        timestamps: Optional[List[float]] = None,
        num_frames: int = 6,
        angle_labels: Optional[List[str]] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract frames from video at specific timestamps using FFmpeg.
        Returns frames as base64-encoded images.
        
        Args:
            video_path: Path to the video file
            timestamps: Specific timestamps to extract (in seconds)
            num_frames: Number of frames to extract if timestamps not provided
            angle_labels: Labels for each angle (front, back, etc.)
            output_dir: Directory for temp files (uses system temp if not provided)
        
        Returns:
            Dict with 'images' list containing frame data
        """
        # Get video duration first
        video_info = self.get_video_info(video_path)
        duration = video_info.get("duration", 5.0)
        
        # Generate timestamps if not provided
        if not timestamps:
            if duration > 0:
                # Evenly space frames across video duration
                timestamps = [duration * i / (num_frames + 1) for i in range(1, num_frames + 1)]
            else:
                timestamps = [0.5 * i for i in range(num_frames)]
        
        # Use temp directory if not provided
        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix="frames_")
        
        try:
            output_paths = []
            
            for i, timestamp in enumerate(timestamps):
                # Clamp timestamp to valid range
                timestamp = max(0, min(timestamp, duration - 0.1)) if duration > 0 else timestamp
                
                output_filename = f"frame_{i:03d}.jpg"
                output_path = os.path.join(output_dir, output_filename)
                
                # FFmpeg command to extract frame at specific timestamp
                cmd = [
                    self.ffmpeg_path,
                    "-ss", str(timestamp),  # Seek BEFORE input (faster)
                    "-i", video_path,
                    "-vframes", "1",
                    "-q:v", "2",  # High quality JPEG
                    "-y",  # Overwrite output
                    output_path
                ]
                
                logger.info(f"Extracting frame at {timestamp}s -> {output_path}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    output_paths.append((timestamp, output_path))
                    logger.info(f"Successfully extracted frame at {timestamp}s")
                else:
                    logger.warning(f"Failed to extract frame at {timestamp}s: {result.stderr[:200] if result.stderr else 'No output'}")
            
            # Convert to base64 images
            images = []
            for i, (timestamp, path) in enumerate(output_paths):
                try:
                    with open(path, "rb") as f:
                        image_data = f.read()
                    
                    base64_image = base64.b64encode(image_data).decode("utf-8")
                    
                    # Determine angle label
                    if angle_labels and i < len(angle_labels):
                        angle = angle_labels[i]
                    else:
                        angle = self._estimate_angle(i, len(output_paths))
                    
                    images.append({
                        "image_base64": f"data:image/jpeg;base64,{base64_image}",
                        "timestamp_sec": round(timestamp, 2),
                        "angle": angle,
                        "frame_index": i
                    })
                except Exception as e:
                    logger.error(f"Error reading frame {path}: {e}")
            
            # Cleanup temp files
            for _, path in output_paths:
                try:
                    os.remove(path)
                except:
                    pass
            try:
                os.rmdir(output_dir)
            except:
                pass
            
            return {
                "total_frames": len(images),
                "video_duration": duration,
                "images": images
            }
            
        except Exception as e:
            logger.error(f"FFmpeg extraction error: {e}")
            return {
                "total_frames": 0,
                "video_duration": duration,
                "images": [],
                "error": str(e)
            }
    
    def _estimate_angle(self, index: int, total: int) -> str:
        """Estimate viewing angle based on frame position"""
        angles = ["front", "front_right", "right", "back", "left", "front_left"]
        if total <= len(angles):
            return angles[index] if index < len(angles) else f"angle_{index}"
        else:
            # For more frames, interpolate
            angle_index = int(index * len(angles) / total)
            return angles[angle_index] if angle_index < len(angles) else f"angle_{index}"
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video information using ffprobe (duration, resolution, etc.)
        """
        try:
            # Use ffprobe for accurate info
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                duration = None
                width = None
                height = None
                
                # Get duration from format
                if "format" in data:
                    duration = float(data["format"].get("duration", 0))
                
                # Get resolution from video stream
                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        width = stream.get("width")
                        height = stream.get("height")
                        if not duration:
                            duration = float(stream.get("duration", 0))
                        break
                
                return {
                    "duration": duration or 5.0,
                    "width": width,
                    "height": height,
                    "path": video_path
                }
            
        except subprocess.TimeoutExpired:
            logger.warning("ffprobe timed out")
        except Exception as e:
            logger.warning(f"ffprobe failed: {e}, falling back to ffmpeg")
        
        # Fallback: use ffmpeg -i
        try:
            cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-f", "null",
                "-"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            duration = None
            for line in result.stderr.split('\n'):
                if "Duration:" in line:
                    duration_str = line.split("Duration:")[1].split(",")[0].strip()
                    parts = duration_str.split(":")
                    if len(parts) == 3:
                        duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                    break
            
            return {
                "duration": duration or 5.0,
                "path": video_path
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {"duration": 5.0, "path": video_path}


# Singleton instance
_ffmpeg_processor = None

def get_ffmpeg_processor() -> FFmpegProcessor:
    global _ffmpeg_processor
    if _ffmpeg_processor is None:
        _ffmpeg_processor = FFmpegProcessor()
    return _ffmpeg_processor
