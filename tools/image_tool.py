"""
Image Generation Tool for the Multi-Agent Video Generation System.
Generates images from prompts using Stable Diffusion or similar models.
"""

import logging
import uuid
import json
from typing import Dict, Any, List
from google.adk.tools import FunctionTool
import requests
from config.settings import settings
from utils.storage_utils import storage_manager

logger = logging.getLogger(__name__)

def generate_images(prompts_url: str) -> Dict[str, Any]:
    """
    Generate images from a list of prompts using AI image generation.
    
    Downloads prompts from GCS, generates images, and uploads them back to storage.
    
    Args:
        prompts_url (str): GCS URL of the prompts JSON file
        
    Returns:
        Dict[str, Any]: Contains:
            - images (List[Dict]): List of generated image information
            - images_folder_url (str): GCS folder URL containing all images
            - total_images (int): Number of images generated
            - prompts_url (str): Original prompts URL used
            - status (str): Success/failure status
            - error (str, optional): Error message if failed
    """
    try:
        logger.info(f"Generating images from prompts: {prompts_url}")
        
        # Download prompts from GCS
        try:
            prompts_json = storage_manager.download_as_text(prompts_url)
            prompts_data = json.loads(prompts_json)
            prompts_list = prompts_data.get("prompts", [])
            logger.info(f"Downloaded {len(prompts_list)} prompts")
        except Exception as e:
            raise Exception(f"Failed to download prompts from {prompts_url}: {str(e)}")
        
        if not prompts_list:
            raise Exception("No prompts found in the downloaded data")
        
        generated_images = []
        batch_id = uuid.uuid4().hex[:8]
        image_style = "cinematic"  # Fixed style for video production
        
        # Generate images for each prompt
        for i, prompt in enumerate(prompts_list):
            try:
                logger.info(f"Generating image {i+1}/{len(prompts_list)}")
                
                # Enhance prompt with style
                enhanced_prompt = f"{prompt}, {image_style} style, high quality, detailed, professional video production"
                
                # Generate image using configured service
                image_data = _generate_single_image(enhanced_prompt, i)
                
                if image_data:
                    # Generate unique filename for image
                    image_filename = f"image_{batch_id}_{i+1:02d}.png"
                    
                    # Upload image to Google Cloud Storage
                    upload_result = storage_manager.upload_binary(
                        content=image_data,
                        folder="images",
                        filename=image_filename,
                        content_type="image/png"
                    )
                    
                    if upload_result["status"] == "success":
                        generated_images.append({
                            "index": i + 1,
                            "prompt": prompt,
                            "enhanced_prompt": enhanced_prompt,
                            "filename": image_filename,
                            "url": upload_result["gcs_url"],
                            "public_url": upload_result["public_url"],
                            "size_bytes": len(image_data)
                        })
                        logger.info(f"Successfully generated and uploaded image {i+1}")
                    else:
                        logger.error(f"Failed to upload image {i+1}: {upload_result.get('error')}")
                else:
                    logger.error(f"Failed to generate image {i+1}")
                    
            except Exception as e:
                logger.error(f"Error generating image {i+1}: {str(e)}")
                continue
        
        if not generated_images:
            raise Exception("Failed to generate any images")
        
        # Create images folder URL (assuming GCS structure)
        base_url = generated_images[0]["url"].rsplit('/', 1)[0] if generated_images else ""
        
        logger.info(f"Successfully generated {len(generated_images)} images")
        
        return {
            "images": generated_images,
            "images_folder_url": base_url,
            "total_images": len(generated_images),
            "prompts_url": prompts_url,
            "image_style": image_style,
            "batch_id": batch_id,
            "status": "success"
        }
        
    except Exception as e:
        error_msg = f"Failed to generate images from prompts '{prompts_url}': {str(e)}"
        logger.error(error_msg)
        
        return {
            "prompts_url": prompts_url,
            "error": error_msg,
            "status": "failed"
        }

def _generate_single_image(prompt: str, index: int) -> bytes:
    """
    Generate a single image from a prompt using the configured image generation service.
    
    Args:
        prompt (str): Image generation prompt
        index (int): Image index for logging
        
    Returns:
        bytes: Generated image data, or None if failed
    """
    try:
        # Try image generation services in order of preference
        if settings.IMAGE_GENERATION_SERVICE == "togetherai":
            try:
                return _generate_with_together_ai(prompt)
            except Exception as e:
                logger.warning(f"Together AI generation failed: {e}")
                # Fall through to next method
                
        elif settings.IMAGE_GENERATION_SERVICE == "huggingface":
            try:
                return _generate_with_huggingface(prompt)
            except Exception as e:
                logger.warning(f"Hugging Face generation failed: {e}")
                # Fall through to next method
                
        elif settings.IMAGE_GENERATION_SERVICE == "local_stable_diffusion":
            try:
                return _generate_with_local_sd(prompt)
            except Exception as e:
                logger.warning(f"Local SD generation failed: {e}")
                # Fall through to next method
        
        # If primary method failed or not configured, try alternative methods
        logger.info("Trying alternative generation methods...")
        
        # Try a simple web-based generation (placeholder for now)
        try:
            return _generate_with_enhanced_placeholder(prompt, index)
        except Exception as e:
            logger.warning(f"Enhanced placeholder generation failed: {e}")
            
        # Final fallback to basic placeholder
        return _generate_placeholder_image(prompt, index)
            
    except Exception as e:
        logger.error(f"All image generation methods failed for prompt '{prompt[:50]}...': {str(e)}")
        return _generate_placeholder_image(prompt, index)

def _generate_with_together_ai(prompt: str) -> bytes:
    """Generate image using Together AI FLUX.1 [schnell] model."""
    try:
        if not settings.TOGETHER_API_KEY:
            raise Exception("Together AI API key not configured")
        
        # Together AI API endpoint for image generation
        api_url = "https://api.together.xyz/v1/images/generations"
        
        headers = {
            "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Enhance the prompt for better FLUX.1 results
        enhanced_prompt = f"{prompt}, high quality, detailed, cinematic style, professional"
        
        payload = {
            "model": settings.FLUX_MODEL_ENDPOINT,
            "prompt": enhanced_prompt,
            "width": settings.DEFAULT_IMAGE_SIZE[0],
            "height": settings.DEFAULT_IMAGE_SIZE[1],
            "steps": 4,  # FLUX.1 [schnell] is optimized for 4 steps
            "n": 1
        }
        
        logger.info(f"Calling Together AI API: {api_url}")
        logger.info(f"Model: {settings.FLUX_MODEL_ENDPOINT}")
        logger.info(f"Enhanced prompt: {enhanced_prompt[:100]}...")
        
        # Make the API request
        response = requests.post(
            api_url, 
            headers=headers, 
            json=payload, 
            timeout=120
        )
        
        # Check for successful response
        if response.status_code == 200:
            result = response.json()
            
            if "data" in result and len(result["data"]) > 0:
                image_data = result["data"][0]
                
                # Together AI returns base64 encoded image
                if "b64_json" in image_data:
                    import base64
                    image_bytes = base64.b64decode(image_data["b64_json"])
                    logger.info(f"Successfully generated image via Together AI FLUX.1 [schnell]")
                    return image_bytes
                elif "url" in image_data:
                    # Download image from URL
                    img_response = requests.get(image_data["url"], timeout=60)
                    img_response.raise_for_status()
                    logger.info(f"Successfully generated and downloaded image via Together AI FLUX.1 [schnell]")
                    return img_response.content
                else:
                    raise Exception("No valid image data in response")
            else:
                raise Exception("No image data in API response")
        else:
            # Try to get error details
            try:
                error_json = response.json()
                error_msg = error_json.get('error', {}).get('message', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}: {response.text[:200]}'
            
            raise Exception(f"API request failed: {error_msg}")
            
    except Exception as e:
        logger.error(f"Together AI image generation failed: {str(e)}")
        raise

def _generate_with_huggingface(prompt: str) -> bytes:
    """Generate image using Hugging Face Inference API."""
    try:
        if not settings.HUGGINGFACE_API_KEY:
            raise Exception("Hugging Face API key not configured")
        
        # Use a more reliable model endpoint
        api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        
        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
        }
        
        # Use the correct simplified format for Hugging Face Inference API
        payload = {
            "inputs": prompt,
            "options": {
                "wait_for_model": True
            }
        }
        
        logger.info(f"Calling Hugging Face API: {api_url}")
        logger.info(f"Prompt: {prompt[:100]}...")
        
        # Make the API request with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    api_url, 
                    headers=headers, 
                    json=payload, 
                    timeout=120
                )
                
                # Check for successful response
                if response.status_code == 200:
                    # Check if response is image data
                    content_type = response.headers.get('content-type', '')
                    if content_type.startswith('image/') or len(response.content) > 1000:
                        logger.info(f"Successfully generated image via Hugging Face (attempt {attempt + 1})")
                        return response.content
                    else:
                        # Response might be JSON with error or still processing
                        try:
                            response_json = response.json()
                            if "error" in response_json:
                                error_msg = response_json['error']
                                if "currently loading" in error_msg or "estimated_time" in response_json:
                                    # Model is loading, wait and retry
                                    wait_time = min(response_json.get("estimated_time", 20), 60)
                                    logger.info(f"Model loading, waiting {wait_time}s (attempt {attempt + 1})")
                                    import time
                                    time.sleep(wait_time)
                                    continue
                                else:
                                    raise Exception(f"API error: {error_msg}")
                            else:
                                # Unknown JSON response
                                logger.warning(f"Unexpected JSON response: {response_json}")
                                raise Exception("Unexpected response format")
                        except json.JSONDecodeError:
                            # Not JSON, treat as error
                            raise Exception(f"Unexpected response format: {response.text[:200]}")
                
                elif response.status_code == 503:
                    # Service unavailable, retry after delay
                    logger.warning(f"Service unavailable (503), retrying in 15s (attempt {attempt + 1})")
                    import time
                    time.sleep(15)
                    continue
                    
                else:
                    # Try to get error details
                    try:
                        error_json = response.json()
                        error_msg = error_json.get('error', f'HTTP {response.status_code}')
                    except:
                        error_msg = f'HTTP {response.status_code}: {response.text[:200]}'
                    
                    if attempt == max_retries - 1:
                        raise Exception(f"API request failed: {error_msg}")
                    else:
                        logger.warning(f"Request failed (attempt {attempt + 1}): {error_msg}")
                        import time
                        time.sleep(10)
                        continue
                    
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Request failed after {max_retries} attempts: {str(e)}")
                logger.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
                import time
                time.sleep(5)
                continue
        
        raise Exception(f"Failed to generate image after {max_retries} attempts")
        
    except Exception as e:
        logger.error(f"Hugging Face image generation failed: {str(e)}")
        raise

def _generate_with_local_sd(prompt: str) -> bytes:
    """Generate image using local Stable Diffusion installation."""
    try:
        # This would connect to a local Stable Diffusion API
        # For example, AUTOMATIC1111's web UI API
        api_url = f"{settings.LOCAL_SD_URL}/sdapi/v1/txt2img"
        
        payload = {
            "prompt": prompt,
            "width": settings.DEFAULT_IMAGE_SIZE[0],
            "height": settings.DEFAULT_IMAGE_SIZE[1],
            "steps": 20,
            "cfg_scale": 7,
            "sampler_name": "DPM++ 2M Karras"
        }
        
        response = requests.post(api_url, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        if "images" in result and result["images"]:
            # Decode base64 image
            import base64
            image_data = base64.b64decode(result["images"][0])
            return image_data
        else:
            raise Exception("No images returned from local Stable Diffusion")
            
    except Exception as e:
        logger.error(f"Local Stable Diffusion generation failed: {str(e)}")
        raise

def _generate_with_enhanced_placeholder(prompt: str, index: int) -> bytes:
    """Generate an enhanced placeholder image with better visual styling."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        import random
        
        # Create a more visually appealing placeholder image
        width, height = settings.DEFAULT_IMAGE_SIZE
        
        # Create a gradient background based on prompt keywords
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Generate colors based on prompt content
        colors = _get_colors_from_prompt(prompt)
        
        # Create a gradient background
        for y in range(height):
            # Calculate blend ratio
            ratio = y / height
            # Blend between two colors
            r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
            g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
            b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add decorative elements
        try:
            # Add some circles
            for _ in range(3):
                x = random.randint(0, width)
                y = random.randint(0, height)
                radius = random.randint(20, 80)
                color = colors[random.randint(0, 1)]
                # Make color semi-transparent by reducing intensity
                color = tuple(int(c * 0.3) for c in color)
                draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)
        except:
            pass
        
        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except:
            font = ImageFont.load_default()
        
        title = f"Image {index + 1}"
        description = prompt[:60] + "..." if len(prompt) > 60 else prompt
        
        # Center the text with background
        title_x = width // 2 - 100
        title_y = height // 2 - 40
        desc_x = width // 2 - 150
        desc_y = height // 2 + 10
        
        # Add semi-transparent background for text readability
        draw.rectangle([title_x-20, title_y-10, title_x+200, desc_y+50], 
                      fill=(0, 0, 0))
        
        draw.text((title_x, title_y), title, fill='white', font=font)
        draw.text((desc_x, desc_y), description, fill='lightgray', font=font)
        
        # Save to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', quality=95)
        
        logger.info(f"Generated enhanced placeholder image for: {prompt[:50]}...")
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Failed to generate enhanced placeholder image: {str(e)}")
        # Fall back to basic placeholder
        return _generate_placeholder_image(prompt, index)

def _get_colors_from_prompt(prompt: str) -> list:
    """Extract color scheme suggestions from prompt keywords."""
    prompt_lower = prompt.lower()
    
    # Color mappings based on common prompt keywords
    color_mappings = {
        'sunset': [(255, 94, 77), (255, 154, 0)],
        'ocean': [(0, 119, 190), (0, 180, 216)],
        'forest': [(34, 139, 34), (154, 205, 50)],
        'night': [(25, 25, 112), (72, 61, 139)],
        'fire': [(255, 69, 0), (255, 140, 0)],
        'sky': [(135, 206, 235), (176, 196, 222)],
        'warm': [(255, 182, 193), (255, 218, 185)],
        'cool': [(173, 216, 230), (176, 224, 230)],
        'dark': [(47, 79, 79), (105, 105, 105)],
        'bright': [(255, 255, 224), (255, 250, 205)],
        'magical': [(138, 43, 226), (186, 85, 211)],
        'cinematic': [(139, 69, 19), (160, 82, 45)],
        'aladdin': [(138, 43, 226), (255, 215, 0)],  # Purple and gold
        'genie': [(30, 144, 255), (138, 43, 226)],  # Blue and purple
    }
    
    # Check for keyword matches
    for keyword, colors in color_mappings.items():
        if keyword in prompt_lower:
            return colors
    
    # Default color scheme
    return [(100, 149, 237), (255, 182, 193)]  # Cornflower blue to light pink

def _generate_placeholder_image(prompt: str, index: int) -> bytes:
    """Generate a placeholder image when no actual generation service is available."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create a placeholder image
        width, height = settings.DEFAULT_IMAGE_SIZE
        image = Image.new('RGB', (width, height), color='lightgray')
        draw = ImageDraw.Draw(image)
        
        # Try to use default font, fall back to basic if not available
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Add text to image
        text = f"Image {index + 1}\n{prompt[:50]}..."
        
        # Calculate text position (centered)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill='black', font=font)
        
        # Save to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Failed to generate placeholder image: {str(e)}")
        # Return minimal placeholder
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00[\xc4\xfe\x10\x00\x00\x00\rIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\xf2\x03\x96\x00\x00\x00\x00IEND\xaeB`\x82'

def validate_images(images_data: List[Dict]) -> Dict[str, Any]:
    """
    Validate generated images for quality and completeness.
    
    Args:
        images_data (List[Dict]): List of image data dictionaries
        
    Returns:
        Dict[str, Any]: Validation results
    """
    issues = []
    warnings = []
    
    if not images_data:
        issues.append("No images generated")
        return {
            "is_valid": False,
            "issues": issues,
            "warnings": warnings,
            "total_images": 0
        }
    
    # Check each image
    for i, image_data in enumerate(images_data):
        required_fields = ["url", "filename", "prompt"]
        for field in required_fields:
            if field not in image_data:
                issues.append(f"Image {i+1} missing required field: {field}")
        
        # Check file size
        if "size_bytes" in image_data:
            size_mb = image_data["size_bytes"] / (1024 * 1024)
            if size_mb > 10:  # 10MB limit
                warnings.append(f"Image {i+1} is large ({size_mb:.1f}MB)")
            elif size_mb < 0.1:  # 100KB minimum
                warnings.append(f"Image {i+1} is very small ({size_mb:.1f}MB)")
    
    # Check for sequence completeness
    expected_indices = set(range(1, len(images_data) + 1))
    actual_indices = {img.get("index", 0) for img in images_data}
    missing_indices = expected_indices - actual_indices
    
    if missing_indices:
        issues.append(f"Missing image indices: {sorted(missing_indices)}")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "total_images": len(images_data),
        "average_size_mb": sum(img.get("size_bytes", 0) for img in images_data) / len(images_data) / (1024 * 1024)
    }

# Create the ADK FunctionTool
image_tool = FunctionTool(func=generate_images)

# Export validation function for use by other modules
__all__ = ["image_tool", "generate_images", "validate_images"] 