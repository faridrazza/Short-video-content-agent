"""
Image Prompt Generation Tool for the Multi-Agent Video Generation System.
Creates detailed image generation prompts from script text using Google Gemini.
"""

import logging
import uuid
from typing import Dict, Any, List
from google.adk.tools import FunctionTool
import google.generativeai as genai
from config.settings import settings
from utils.storage_utils import storage_manager

logger = logging.getLogger(__name__)

def generate_prompts(script_url: str) -> Dict[str, Any]:
    """
    Generate detailed image generation prompts from a script.
    
    Analyzes the script content and creates 3-4 detailed, cinematic prompts
    that capture key visual moments for video production.
    
    Args:
        script_url (str): GCS URL of the script file
        
    Returns:
        Dict[str, Any]: Contains:
            - prompts (List[str]): List of detailed image generation prompts
            - prompts_url (str): GCS URL of the stored prompts file
            - script_url (str): Original script URL used
            - num_prompts (int): Number of prompts generated
            - status (str): Success/failure status
            - error (str, optional): Error message if failed
    """
    try:
        logger.info(f"Generating image prompts from script: {script_url}")
        
        # Download script from GCS
        try:
            script_text = storage_manager.download_as_text(script_url)
            logger.info(f"Downloaded script: {len(script_text)} characters")
        except Exception as e:
            raise Exception(f"Failed to download script from {script_url}: {str(e)}")
        
        # Configure Gemini API
        if settings.GOOGLE_GENAI_USE_VERTEXAI:
            # Use Vertex AI configuration
            genai.configure()
        else:
            # Use API key configuration
            genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Create detailed prompt for image prompt generation
        num_images = 4  # Fixed number of images for video
        prompt = f"""Create {num_images} simple, clear image generation prompts based on this video script:

"{script_text}"

Requirements for each prompt:
- Keep each prompt under 100 words
- Use simple, clear descriptions
- Focus on ONE main visual element per prompt
- Avoid technical camera terms or complex artistic references
- Use descriptive adjectives for mood and style
- Make them suitable for AI image generation (Stable Diffusion style)
- Focus on characters, settings, and actions that tell the story

Example format: "Aladdin, a young man in simple clothes, sitting in a dark cave holding a glowing golden lamp, magical light emanating from the lamp, mystical atmosphere, warm golden lighting"

Generate exactly {num_images} simple prompts, one per line, numbered 1-{num_images}:"""

        # Initialize Gemini model
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Generate prompts
        response = model.generate_content(prompt)
        prompts_text = response.text.strip()
        
        # Parse prompts into individual items
        prompts_lines = prompts_text.split('\n')
        prompts_list = []
        
        for line in prompts_lines:
            line = line.strip()
            if line and not line.isspace():
                # Remove numbering if present (e.g., "1. " or "1)")
                if line[0].isdigit():
                    # Find the first space or period after the number
                    for i, char in enumerate(line):
                        if char in ['.', ')', ' '] and i > 0:
                            line = line[i+1:].strip()
                            break
                prompts_list.append(line)
        
        # Ensure we have the right number of prompts
        if len(prompts_list) < num_images:
            logger.warning(f"Generated only {len(prompts_list)} prompts, expected {num_images}")
        prompts_list = prompts_list[:num_images]  # Take only requested number
        
        # Generate unique filename
        prompts_filename = f"prompts_{uuid.uuid4().hex[:8]}.json"
        
        # Create structured data for storage
        prompts_data = {
            "script_url": script_url,
            "script_text": script_text,
            "prompts": prompts_list,
            "num_prompts": len(prompts_list),
            "generation_timestamp": str(uuid.uuid4())
        }
        
        # Upload prompts to Google Cloud Storage
        import json
        prompts_json = json.dumps(prompts_data, indent=2)
        upload_result = storage_manager.upload_text(
            content=prompts_json,
            folder="prompts",
            filename=prompts_filename
        )
        
        if upload_result["status"] != "success":
            raise Exception(f"Failed to upload prompts: {upload_result.get('error', 'Unknown error')}")
        
        logger.info(f"Successfully generated {len(prompts_list)} image prompts")
        
        return {
            "prompts": prompts_list,
            "prompts_url": upload_result["gcs_url"],
            "public_url": upload_result["public_url"],
            "script_url": script_url,
            "num_prompts": len(prompts_list),
            "filename": prompts_filename,
            "status": "success"
        }
        
    except Exception as e:
        error_msg = f"Failed to generate prompts from script '{script_url}': {str(e)}"
        logger.error(error_msg)
        
        return {
            "script_url": script_url,
            "error": error_msg,
            "status": "failed"
        }

def validate_prompts(prompts: List[str]) -> Dict[str, Any]:
    """
    Validate generated prompts for quality and completeness.
    
    Args:
        prompts (List[str]): List of image generation prompts
        
    Returns:
        Dict[str, Any]: Validation results with quality scores
    """
    issues = []
    suggestions = []
    quality_scores = []
    
    for i, prompt in enumerate(prompts):
        score = 0
        prompt_issues = []
        
        # Check length
        if len(prompt) < 20:
            prompt_issues.append(f"Prompt {i+1} is very short")
        elif len(prompt) > 300:
            prompt_issues.append(f"Prompt {i+1} is very long")
        else:
            score += 25
        
        # Check for visual elements
        visual_keywords = ['lighting', 'composition', 'camera', 'scene', 'cinematic', 'visual']
        visual_count = sum(1 for keyword in visual_keywords if keyword.lower() in prompt.lower())
        if visual_count > 0:
            score += min(visual_count * 10, 25)
        else:
            prompt_issues.append(f"Prompt {i+1} lacks visual descriptors")
        
        # Check for specificity
        specific_keywords = ['detailed', 'specific', 'close-up', 'wide shot', 'angle', 'style']
        specific_count = sum(1 for keyword in specific_keywords if keyword.lower() in prompt.lower())
        if specific_count > 0:
            score += min(specific_count * 5, 25)
        
        # Check for mood/atmosphere
        mood_keywords = ['mood', 'atmosphere', 'dramatic', 'bright', 'dark', 'warm', 'cool']
        mood_count = sum(1 for keyword in mood_keywords if keyword.lower() in prompt.lower())
        if mood_count > 0:
            score += min(mood_count * 5, 25)
        
        quality_scores.append(score)
        issues.extend(prompt_issues)
    
    # Overall suggestions
    avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    if avg_score < 50:
        suggestions.append("Consider adding more visual and cinematic details")
    if len(set(quality_scores)) == 1:
        suggestions.append("Prompts seem very similar - add more variety")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "quality_scores": quality_scores,
        "average_quality": avg_score,
        "total_prompts": len(prompts)
    }

# Create the ADK FunctionTool
prompt_tool = FunctionTool(func=generate_prompts)

# Export validation function for use by other modules
__all__ = ["prompt_tool", "generate_prompts", "validate_prompts"] 