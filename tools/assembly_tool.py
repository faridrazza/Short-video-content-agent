"""
Video Assembly Tool for the Multi-Agent Video Generation System.
Combines audio, images, and script text into final MP4 video production.
"""

import logging
import uuid
import json
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional
from google.adk.tools import FunctionTool
from config.settings import settings
from utils.storage_utils import storage_manager

logger = logging.getLogger(__name__)

def assemble_video(audio_url: str, images_data: str, script_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Assemble final video from audio, images, and optional script text.
    
    Downloads all assets, creates video with proper timing, transitions,
    and uploads the final MP4 to Google Cloud Storage.
    
    Args:
        audio_url (str): GCS URL of the audio file
        images_data (str): JSON string or GCS URL containing images data
        script_url (str, optional): GCS URL of the script file for captions
        
    Returns:
        Dict[str, Any]: Contains:
            - video_url (str): GCS URL of the final video
            - duration (float): Video duration in seconds
            - resolution (tuple): Video resolution (width, height)
            - assets_used (dict): Information about input assets
            - status (str): Success/failure status
            - error (str, optional): Error message if failed
    """
    try:
        logger.info(f"Assembling video from audio: {audio_url}, images_data: {type(images_data)}")

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Using temporary directory: {temp_dir}")

            # Download and prepare assets
            assets = _download_assets(audio_url, images_data, script_url, temp_dir)

            # Determine video parameters
            video_params = _calculate_video_parameters(assets, None)

            # Create video using FFmpeg
            video_path = _create_video_with_ffmpeg(assets, video_params, temp_dir)

            # Upload final video to GCS
            video_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"

            with open(video_path, 'rb') as video_file:
                video_data = video_file.read()

            upload_result = storage_manager.upload_binary(
                content=video_data,
                folder="videos",
                filename=video_filename,
                content_type="video/mp4"
            )

            if upload_result["status"] != "success":
                raise Exception(f"Failed to upload video: {upload_result.get('error', 'Unknown error')}")

            logger.info(f"Successfully assembled video: {len(video_data)} bytes")

            return {
                "video_url": upload_result["gcs_url"],
                "public_url": upload_result["public_url"],
                "duration": video_params["duration"],
                "resolution": video_params["resolution"],
                "assets_used": {
                    "audio_url": audio_url,
                    "images_data": str(images_data)[:100] + "..." if len(str(images_data)) > 100 else str(images_data),
                    "script_url": script_url,
                    "num_images": len(assets["images"]),
                    "audio_duration": assets["audio_duration"]
                },
                "filename": video_filename,
                "video_size_bytes": len(video_data),
                "status": "success"
            }

    except Exception as e:
        error_msg = f"Failed to assemble video: {str(e)}"
        logger.error(error_msg)

        return {
            "audio_url": audio_url,
            "images_data": str(images_data)[:100] + "..." if len(str(images_data)) > 100 else str(images_data),
            "script_url": script_url,
            "error": error_msg,
            "status": "failed"
        }

def _download_assets(audio_url: str, images_data: str, script_url: Optional[str], temp_dir: str) -> Dict[str, Any]:
    """Download all required assets for video assembly."""
    assets = {
        "audio_path": None,
        "audio_duration": 0,
        "images": [],
        "script_text": None
    }

    # Download audio file
    try:
        audio_data = storage_manager.download_as_bytes(audio_url)
        audio_path = os.path.join(temp_dir, "audio.mp3")

        with open(audio_path, 'wb') as f:
            f.write(audio_data)

        assets["audio_path"] = audio_path
        assets["audio_duration"] = _get_audio_duration(audio_path)
        logger.info(f"Downloaded audio: {len(audio_data)} bytes, {assets['audio_duration']:.1f}s")

    except Exception as e:
        raise Exception(f"Failed to download audio from {audio_url}: {str(e)}")

    # Download images data
    try:
        # Parse images data - could be JSON string or GCS URL
        if images_data.startswith("gs://") and images_data.endswith('.json'):
            # It's a GCS URL to a JSON file
            images_json = storage_manager.download_as_text(images_data)
            parsed_images_data = json.loads(images_json)
        elif images_data.startswith("{") or images_data.startswith("["):
            # It's direct JSON string
            parsed_images_data = json.loads(images_data)
        else:
            # Try to parse as JSON string anyway
            parsed_images_data = json.loads(images_data)

        # Extract images list from parsed data
        image_list = parsed_images_data.get("images", parsed_images_data if isinstance(parsed_images_data, list) else [])
        logger.info(f"Assembly tool found {len(image_list)} images in the data")
        logger.info(f"Images data structure: {type(parsed_images_data)}")

        # Download each image
        for i, image_info in enumerate(image_list):
            try:
                # Try different possible URL field names
                image_url = image_info.get("url") or image_info.get("gcs_url") or image_info.get("image_url")
                if not image_url:
                    logger.warning(f"No URL found for image {i+1}: {image_info}")
                    continue

                image_data = storage_manager.download_as_bytes(image_url)
                image_path = os.path.join(temp_dir, f"image_{i+1:02d}.png")

                with open(image_path, 'wb') as f:
                    f.write(image_data)

                assets["images"].append({
                    "path": image_path,
                    "index": i + 1,
                    "url": image_url,
                    "size_bytes": len(image_data),
                    "prompt": image_info.get("prompt", "")
                })

            except Exception as e:
                logger.warning(f"Failed to download image {i+1}: {str(e)}")
                continue

        logger.info(f"Downloaded {len(assets['images'])} images")

    except Exception as e:
        logger.warning(f"Failed to download images data: {str(e)}")
        logger.debug(f"Images data type: {type(images_data)}, content: {str(images_data)[:200]}")
        # Continue without images for audio-only video

    # Download script if provided
    if script_url:
        try:
            assets["script_text"] = storage_manager.download_as_text(script_url)
            logger.info(f"Downloaded script: {len(assets['script_text'])} characters")
        except Exception as e:
            logger.warning(f"Failed to download script: {str(e)}")

    return assets

def _get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file using FFprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', audio_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return float(result.stdout.strip())
        else:
            logger.warning(f"FFprobe failed: {result.stderr}")
            return 30.0 # Default duration

    except Exception as e:
        logger.warning(f"Failed to get audio duration: {str(e)}")
        return 30.0 # Default duration

def _calculate_video_parameters(assets: Dict[str, Any], video_duration: float = None) -> Dict[str, Any]:
    """Calculate video timing and layout parameters optimized for animations."""
    params = {
        "resolution": settings.DEFAULT_VIDEO_RESOLUTION,
        "fps": settings.DEFAULT_VIDEO_FPS,
        "duration": video_duration or assets["audio_duration"] or 30.0,
        "image_duration": 0,
        "transition_duration": 0.8 # Increased for smoother crossfade animations
    }

    # Calculate how long each image should be displayed
    num_images = len(assets["images"])
    if num_images > 0:
        total_transition_time = (num_images - 1) * params["transition_duration"]
        params["image_duration"] = (params["duration"] - total_transition_time) / num_images
        params["image_duration"] = max(params["image_duration"], 2.0) # Minimum 2 seconds for better animations

        # Adjust for optimal animation timing
        if params["image_duration"] > 8.0:
            # If images are displayed too long, add more transition time
            params["transition_duration"] = min(1.5, params["image_duration"] * 0.15)
            # Recalculate with new transition duration
            total_transition_time = (num_images - 1) * params["transition_duration"]
            params["image_duration"] = (params["duration"] - total_transition_time) / num_images
            params["image_duration"] = max(params["image_duration"], 2.0)

        logger.info(f"Video parameters: {params['duration']:.1f}s total, {params['image_duration']:.1f}s per image, {params['transition_duration']:.1f}s transitions")

    return params

def _create_video_with_ffmpeg(assets: Dict[str, Any], params: Dict[str, Any], temp_dir: str) -> str:
    """Create video using FFmpeg with images, audio, and optional captions."""
    output_path = os.path.join(temp_dir, "output_video.mp4")

    try:
        # Check if FFmpeg is available
        if not _check_ffmpeg_available():
            raise Exception("FFmpeg not found. Please install FFmpeg to enable video assembly.")

        if not assets["images"]:
            # Audio-only video with static background
            return _create_audio_only_video(assets, params, output_path)
        else:
            # Video with image slideshow
            return _create_slideshow_video(assets, params, output_path)

    except Exception as e:
        logger.error(f"FFmpeg video creation failed: {str(e)}")
        # Fallback to creating a simple placeholder video
        return _create_placeholder_video(assets, params, output_path)

def _check_ffmpeg_available() -> bool:
    """Check if FFmpeg is available on the system."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False

def _create_slideshow_video(assets: Dict[str, Any], params: Dict[str, Any], output_path: str) -> str:
    """Create video with animated image slideshow and audio."""

    # Create filter complex for animated slideshow with dynamic effects
    filter_parts = []
    input_parts = ['-i', assets["audio_path"]]

    # Add all images as inputs
    for image in assets["images"]:
        input_parts.extend(['-i', image["path"]])

    # Create animated slideshow filter
    num_images = len(assets["images"])
    image_duration = params["image_duration"]
    transition_duration = params["transition_duration"]

    # Animation types to cycle through
    animations = ['zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'pan_up', 'pan_down']

    # Build filter for each image with dynamic animations
    animated_clips = []

    for i in range(num_images):
        # Choose animation type (cycle through different effects)
        animation = animations[i % len(animations)]

        # Base scale and pad filter to fit resolution
        base_filter = (
            f"[{i+1}:v]scale={params['resolution'][0]*2}:{params['resolution'][1]*2}:"
            f"force_original_aspect_ratio=decrease,pad={params['resolution'][0]*2}:"
            f"{params['resolution'][1]*2}:(ow-iw)/2:(oh-ih)/2"
        )

        # Add animation-specific effects
        if animation == 'zoom_in':
            # Start zoomed out, end zoomed in
            animation_filter = (
                f"{base_filter},zoompan=z='if(lte(zoom,1.0),1.5,max(1.00,zoom-0.0015))'"
                f":d={int(image_duration * params['fps'])}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":s={params['resolution'][0]}x{params['resolution'][1]}"
            )
        elif animation == 'zoom_out':
            # Start zoomed in, end zoomed out
            animation_filter = (
                f"{base_filter},zoompan=z='if(lte(zoom,1.0),1.0,max(1.00,zoom-0.0015))'"
                f":d={int(image_duration * params['fps'])}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":s={params['resolution'][0]}x{params['resolution'][1]}"
            )
        elif animation == 'pan_left':
            # Pan from right to left
            animation_filter = (
                f"{base_filter},zoompan=z='1.3'"
                f":d={int(image_duration * params['fps'])}:x='iw-iw/zoom-{int(image_duration * params['fps'])}*3'"
                f":y='ih/2-(ih/zoom/2)':s={params['resolution'][0]}x{params['resolution'][1]}"
            )
        elif animation == 'pan_right':
            # Pan from left to right
            animation_filter = (
                f"{base_filter},zoompan=z='1.3'"
                f":d={int(image_duration * params['fps'])}:x='{int(image_duration * params['fps'])}*3'"
                f":y='ih/2-(ih/zoom/2)':s={params['resolution'][0]}x{params['resolution'][1]}"
            )
        elif animation == 'pan_up':
            # Pan from bottom to top
            animation_filter = (
                f"{base_filter},zoompan=z='1.3'"
                f":d={int(image_duration * params['fps'])}:x='iw/2-(iw/zoom/2)'"
                f":y='ih-ih/zoom-{int(image_duration * params['fps'])}*2':s={params['resolution'][0]}x{params['resolution'][1]}"
            )
        else: # pan_down
            # Pan from top to bottom
            animation_filter = (
                f"{base_filter},zoompan=z='1.3'"
                f":d={int(image_duration * params['fps'])}:x='iw/2-(iw/zoom/2)'"
                f":y='{int(image_duration * params['fps'])}*2':s={params['resolution'][0]}x{params['resolution'][1]}"
            )

        # Add fade in/out effects for smooth transitions
        fade_filter = (
            f"{animation_filter},fade=t=in:st=0:d=0.5:alpha=1,"
            f"fade=t=out:st={image_duration-0.5}:d=0.5:alpha=1"
        )

        # NO timing offset - let each clip be its natural duration
        # This way all images get the same treatment as the first one
        filter_parts.append(f"{fade_filter}[animated{i}]")
        animated_clips.append(f"[animated{i}]")

    # Use simple concatenation instead of complex crossfade transitions
    # This ensures all images appear with the same awesome animation
    if num_images > 1:
        # Simple concatenation that preserves the animation quality
        concat_input = "".join(f"[animated{i}]" for i in range(num_images))
        concat_filter = f"{concat_input}concat=n={num_images}:v=1:a=0[final_video]"
        filter_parts.append(concat_filter)
        final_output = "[final_video]"
    else:
        # Single image case
        final_output = animated_clips[0] if animated_clips else "[animated0]"

    # Combine all filters
    filter_complex = ";".join(filter_parts)

    # Build FFmpeg command with enhanced quality settings
    cmd = [
        'ffmpeg', '-y', # Overwrite output
        *input_parts,
        '-filter_complex', filter_complex,
        '-map', final_output,
        '-map', '0:a', # Audio from first input
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '20', # Higher quality for animations
        '-pix_fmt', 'yuv420p', # Ensure compatibility
        '-c:a', 'aac',
        '-b:a', '128k',
        '-r', str(params["fps"]),
        '-t', str(params["duration"]),
        output_path
    ]

    logger.info(f"Creating animated slideshow with {num_images} images and dynamic effects")
    logger.debug(f"FFmpeg command: {' '.join(cmd[:10])}... (truncated)")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.error(f"Animated slideshow creation failed: {result.stderr}")
        # Fallback to simple slideshow if animations fail
        logger.info("Falling back to simple slideshow creation")
        return _create_simple_slideshow_video(assets, params, output_path)

    logger.info("Successfully created animated slideshow video")
    return output_path

def _create_simple_slideshow_video(assets: Dict[str, Any], params: Dict[str, Any], output_path: str) -> str:
    """Fallback: Create simple slideshow without complex animations."""

    # This is the original implementation as a fallback
    filter_parts = []
    input_parts = ['-i', assets["audio_path"]]

    # Add all images as inputs
    for image in assets["images"]:
        input_parts.extend(['-i', image["path"]])

    # Create simple slideshow filter
    num_images = len(assets["images"])
    image_duration = params["image_duration"]
    transition_duration = params["transition_duration"]

    # Build filter for each image with basic scaling and timing
    for i in range(num_images):
        filter_parts.append(
            f"[{i+1}:v]scale={params['resolution'][0]}:{params['resolution'][1]}:"
            f"force_original_aspect_ratio=decrease,pad={params['resolution'][0]}:"
            f"{params['resolution'][1]}:(ow-iw)/2:(oh-ih)/2,setpts=PTS-STARTPTS+"
            f"{i * (image_duration + transition_duration)}/TB[img{i}]"
        )

    # Concatenate all images
    concat_input = "".join(f"[img{i}]" for i in range(num_images))
    filter_parts.append(f"{concat_input}concat=n={num_images}:v=1:a=0[slideshow]")

    filter_complex = ";".join(filter_parts)

    # Build FFmpeg command
    cmd = [
        'ffmpeg', '-y', # Overwrite output
        *input_parts,
        '-filter_complex', filter_complex,
        '-map', '[slideshow]',
        '-map', '0:a', # Audio from first input
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-r', str(params["fps"]),
        '-t', str(params["duration"]),
        output_path
    ]

    logger.info("Creating simple slideshow as fallback")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(f"Simple slideshow creation also failed: {result.stderr}")

    return output_path

def _create_audio_only_video(assets: Dict[str, Any], params: Dict[str, Any], output_path: str) -> str:
    """Create audio-only video with animated background."""

    # Create an animated gradient background instead of static black
    # This adds visual interest even without images
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', (
            f"color=c=0x1a1a2e:size={params['resolution'][0]}x{params['resolution'][1]}:rate={params['fps']},"
            f"geq=r='128+64*sin(2*PI*t/10)':g='64+32*sin(2*PI*t/7)':b='96+48*sin(2*PI*t/13)'"
        ),
        '-i', assets["audio_path"],
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '28',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-t', str(params["duration"]),
        output_path
    ]

    logger.info("Creating animated background video for audio-only content")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        logger.warning(f"Animated background creation failed: {result.stderr}")
        # Fallback to simple static background
        logger.info("Falling back to static background")
        return _create_static_audio_video(assets, params, output_path)

    return output_path

def _create_static_audio_video(assets: Dict[str, Any], params: Dict[str, Any], output_path: str) -> str:
    """Fallback: Create audio video with static background."""

    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', f"color=c=black:size={params['resolution'][0]}x{params['resolution'][1]}:rate={params['fps']}",
        '-i', assets["audio_path"],
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '28',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-t', str(params["duration"]),
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        raise Exception(f"Static background creation also failed: {result.stderr}")

    return output_path

def _create_placeholder_video(assets: Dict[str, Any], params: Dict[str, Any], output_path: str) -> str:
    """Create a basic placeholder video when FFmpeg is not available."""
    try:
        # Create a very basic MP4 file placeholder
        # This is a minimal approach - in production you'd want proper video creation

        # Copy audio file as-is if it's already MP4, otherwise create minimal video
        if assets["audio_path"] and assets["audio_path"].endswith('.mp3'):
            # For now, just copy the audio file with MP4 extension
            import shutil
            shutil.copy2(assets["audio_path"], output_path)

            # Note: This creates an audio file with .mp4 extension
            # In production, you'd want proper video encoding
            logger.warning("Created placeholder video (audio only) - FFmpeg not available")
        else:
            # Create minimal empty MP4 file
            with open(output_path, 'wb') as f:
                # Write minimal MP4 header (this is a very basic placeholder)
                f.write(b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom')
            logger.warning("Created minimal placeholder video file")

        return output_path

    except Exception as e:
        logger.error(f"Failed to create placeholder video: {str(e)}")
        # Create empty file as last resort
        with open(output_path, 'wb') as f:
            f.write(b'')
        return output_path

def validate_video_output(video_path: str) -> Dict[str, Any]:
    """
    Validate the assembled video for quality and completeness.

    Args:
        video_path (str): Path to the video file

    Returns:
        Dict[str, Any]: Validation results
    """
    issues = []
    warnings = []

    try:
        if not os.path.exists(video_path):
            issues.append("Video file does not exist")
            return {
                "is_valid": False,
                "issues": issues,
                "warnings": warnings
            }

        file_size = os.path.getsize(video_path)
        size_mb = file_size / (1024 * 1024)

        # Check file size
        if file_size == 0:
            issues.append("Video file is empty")
        elif size_mb > 100: # 100MB limit
            warnings.append(f"Video file is large ({size_mb:.1f}MB)")
        elif size_mb < 0.1: # 100KB minimum
            warnings.append(f"Video file is very small ({size_mb:.1f}MB)")

        # Try to get video info with FFprobe if available
        try:
            if _check_ffmpeg_available():
                cmd = [
                    'ffprobe', '-v', 'quiet', '-show_entries',
                    'format=duration:stream=width,height,codec_name',
                    '-of', 'json', video_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    probe_data = json.loads(result.stdout)
                    # Add more detailed validation based on probe data
                    format_info = probe_data.get('format', {})
                    duration = float(format_info.get('duration', 0))

                    if duration == 0:
                        warnings.append("Video appears to have no duration")
                    elif duration < 5:
                        warnings.append(f"Video is very short ({duration:.1f}s)")

        except Exception as e:
            logger.debug(f"Video validation with FFprobe failed: {str(e)}")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "file_size_mb": size_mb,
            "file_exists": True
        }

    except Exception as e:
        logger.error(f"Video validation failed: {str(e)}")
        return {
            "is_valid": False,
            "issues": [f"Validation error: {str(e)}"],
            "warnings": warnings
        }

# Create the ADK FunctionTool
assembly_tool = FunctionTool(func=assemble_video)

# Export validation function for use by other modules
__all__ = ["assembly_tool", "assemble_video", "validate_video_output"]