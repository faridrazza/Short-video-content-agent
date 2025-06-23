"""
Debug utility to trace prompt and image generation flow.
"""

import logging
import json
from utils.storage_utils import storage_manager

logger = logging.getLogger(__name__)

def debug_prompt_flow(prompts_url: str) -> dict:
    """
    Debug the prompt generation to image generation flow.
    
    Args:
        prompts_url: GCS URL of the prompts JSON file
        
    Returns:
        dict: Debug information about the flow
    """
    try:
        # Download and analyze prompts
        prompts_json = storage_manager.download_as_text(prompts_url)
        prompts_data = json.loads(prompts_json)
        
        debug_info = {
            "prompts_url": prompts_url,
            "prompts_data_keys": list(prompts_data.keys()),
            "prompts_count": len(prompts_data.get("prompts", [])),
            "prompts_list": prompts_data.get("prompts", []),
            "num_prompts_field": prompts_data.get("num_prompts", "not_found"),
            "status": "success"
        }
        
        logger.info(f"DEBUG FLOW - Prompts URL: {prompts_url}")
        logger.info(f"DEBUG FLOW - Found {debug_info['prompts_count']} prompts")
        logger.info(f"DEBUG FLOW - Data keys: {debug_info['prompts_data_keys']}")
        
        for i, prompt in enumerate(debug_info['prompts_list']):
            logger.info(f"DEBUG FLOW - Prompt {i+1}: {prompt[:80]}...")
            
        return debug_info
        
    except Exception as e:
        error_info = {
            "prompts_url": prompts_url,
            "error": str(e),
            "status": "failed"
        }
        logger.error(f"DEBUG FLOW - Error: {str(e)}")
        return error_info

def debug_image_data(images_data_str: str) -> dict:
    """
    Debug the images data passed to assembly tool.
    
    Args:
        images_data_str: JSON string or GCS URL with images data
        
    Returns:
        dict: Debug information about images data
    """
    try:
        # Parse images data - could be JSON string or GCS URL
        if images_data_str.startswith("gs://") and images_data_str.endswith('.json'):
            # It's a GCS URL to a JSON file
            images_json = storage_manager.download_as_text(images_data_str)
            parsed_images_data = json.loads(images_json)
            source_type = "GCS_URL"
        elif images_data_str.startswith("{") or images_data_str.startswith("["):
            # It's direct JSON string
            parsed_images_data = json.loads(images_data_str)
            source_type = "JSON_STRING"
        else:
            # Try to parse as JSON string anyway
            parsed_images_data = json.loads(images_data_str)
            source_type = "UNKNOWN_JSON"

        # Extract images list from parsed data
        image_list = parsed_images_data.get("images", parsed_images_data if isinstance(parsed_images_data, list) else [])
        
        debug_info = {
            "source_type": source_type,
            "images_data_keys": list(parsed_images_data.keys()) if isinstance(parsed_images_data, dict) else "not_dict",
            "images_count": len(image_list),
            "total_images_field": parsed_images_data.get("total_images", "not_found") if isinstance(parsed_images_data, dict) else "not_dict",
            "image_urls": [img.get("url", "no_url") for img in image_list if isinstance(img, dict)],
            "status": "success"
        }
        
        logger.info(f"DEBUG IMAGES - Source: {source_type}")
        logger.info(f"DEBUG IMAGES - Found {debug_info['images_count']} images")
        logger.info(f"DEBUG IMAGES - Data keys: {debug_info['images_data_keys']}")
        
        for i, img in enumerate(image_list):
            if isinstance(img, dict):
                logger.info(f"DEBUG IMAGES - Image {i+1}: {img.get('filename', 'no_filename')} - {img.get('url', 'no_url')}")
            
        return debug_info
        
    except Exception as e:
        error_info = {
            "images_data_str": images_data_str[:200] + "..." if len(images_data_str) > 200 else images_data_str,
            "error": str(e),
            "status": "failed"
        }
        logger.error(f"DEBUG IMAGES - Error: {str(e)}")
        return error_info 