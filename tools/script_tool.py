"""
Script Generation Tool for the Multi-Agent Video Generation System.
Generates engaging video scripts from input topics using Google Gemini.
"""

import logging
import uuid
from typing import Dict, Any
from google.adk.tools import FunctionTool
import google.generativeai as genai
from config.settings import settings
from utils.storage_utils import storage_manager

logger = logging.getLogger(__name__)

def generate_script(topic: str) -> Dict[str, Any]:
    """
    Generate a compelling video script from a given topic using Gemini.
    
    This function creates a 3-5 sentence video script that is engaging, 
    informative, and suitable for a 30-60 second video. The script focuses 
    on key points that can be easily visualized.
    
    Args:
        topic (str): The topic for the video script
        
    Returns:
        Dict[str, Any]: Contains:
            - script (str): The generated script text
            - script_url (str): GCS URL of the stored script
            - word_count (int): Number of words in the script
            - estimated_duration (float): Estimated reading time in seconds
            - status (str): Success/failure status
            - error (str, optional): Error message if failed
    """
    try:
        logger.info(f"Generating script for topic: {topic}")
        
        # Configure Gemini API
        if settings.GOOGLE_GENAI_USE_VERTEXAI:
            # Use Vertex AI configuration
            genai.configure()
        else:
            # Use API key configuration
            genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Create detailed prompt for script generation
        prompt = f"""Create a compelling and engaging video script about "{topic}".

Requirements:
- Write exactly 3-5 sentences
- Make it informative and engaging for a general audience
- Focus on key points that can be visualized in images
- Use clear, conversational language
- Keep it suitable for a 30-60 second video
- Include a strong opening and compelling conclusion
- Make each sentence flow naturally to the next

Topic: {topic}

Generate only the script text, no additional formatting or explanations."""

        # Initialize Gemini model
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Generate script content
        response = model.generate_content(prompt)
        script_text = response.text.strip()
        
        # Validate script length
        if len(script_text) > settings.MAX_SCRIPT_LENGTH:
            logger.warning(f"Generated script exceeds max length: {len(script_text)} chars")
            # Truncate if too long
            script_text = script_text[:settings.MAX_SCRIPT_LENGTH]
        
        # Calculate metrics
        word_count = len(script_text.split())
        estimated_duration = word_count * 0.4  # Approximate 150 words per minute
        
        # Generate unique filename
        script_filename = f"script_{uuid.uuid4().hex[:8]}.txt"
        
        # Upload script to Google Cloud Storage
        upload_result = storage_manager.upload_text(
            content=script_text,
            folder="scripts",
            filename=script_filename
        )
        
        if upload_result["status"] != "success":
            raise Exception(f"Failed to upload script: {upload_result.get('error', 'Unknown error')}")
        
        logger.info(f"Successfully generated script: {word_count} words, ~{estimated_duration:.1f}s duration")
        
        return {
            "script": script_text,
            "script_url": upload_result["gcs_url"],
            "public_url": upload_result["public_url"],
            "word_count": word_count,
            "estimated_duration": estimated_duration,
            "topic": topic,
            "filename": script_filename,
            "status": "success"
        }
        
    except Exception as e:
        error_msg = f"Failed to generate script for topic '{topic}': {str(e)}"
        logger.error(error_msg)
        
        return {
            "topic": topic,
            "error": error_msg,
            "status": "failed"
        }

def validate_script_content(script: str) -> Dict[str, Any]:
    """
    Validate script content for quality and requirements.
    
    Args:
        script (str): Script text to validate
        
    Returns:
        Dict[str, Any]: Validation results with suggestions
    """
    issues = []
    suggestions = []
    
    # Check sentence count
    sentences = script.split('.')
    sentence_count = len([s for s in sentences if s.strip()])
    
    if sentence_count < 3:
        issues.append("Script has fewer than 3 sentences")
        suggestions.append("Add more content to reach 3-5 sentences")
    elif sentence_count > 5:
        issues.append("Script has more than 5 sentences")
        suggestions.append("Consider condensing to 3-5 sentences")
    
    # Check length
    if len(script) < 50:
        issues.append("Script is very short")
        suggestions.append("Add more descriptive content")
    elif len(script) > settings.MAX_SCRIPT_LENGTH:
        issues.append(f"Script exceeds maximum length of {settings.MAX_SCRIPT_LENGTH} characters")
        suggestions.append("Reduce script length")
    
    # Check for visual elements
    visual_keywords = ['see', 'show', 'display', 'visual', 'image', 'picture', 'view', 'look']
    has_visual_elements = any(keyword in script.lower() for keyword in visual_keywords)
    
    if not has_visual_elements:
        suggestions.append("Consider adding more visual elements that can be illustrated")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "sentence_count": sentence_count,
        "character_count": len(script),
        "word_count": len(script.split())
    }

# Create the ADK FunctionTool
script_tool = FunctionTool(func=generate_script)

# Export validation function for use by other modules
__all__ = ["script_tool", "generate_script", "validate_script_content"] 