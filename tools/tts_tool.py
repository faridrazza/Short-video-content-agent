"""
Text-to-Speech Tool for the Multi-Agent Video Generation System.
Converts script text to audio narration using Google Cloud Text-to-Speech.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from google.adk.tools import FunctionTool
from google.cloud import texttospeech
from config.settings import settings
from utils.storage_utils import storage_manager

logger = logging.getLogger(__name__)

def text_to_speech(script_url: str) -> Dict[str, Any]:
    """
    Convert script text to audio using Google Cloud Text-to-Speech.
    
    Downloads the script from GCS, synthesizes speech, and uploads the audio back to GCS.
    
    Args:
        script_url (str): GCS URL of the script file
        
    Returns:
        Dict[str, Any]: Contains:
            - audio_url (str): GCS URL of the generated audio
            - duration (float): Audio duration in seconds
            - voice_used (str): Voice name that was used
            - audio_config (dict): Audio configuration details
            - status (str): Success/failure status
            - error (str, optional): Error message if failed
    """
    try:
        logger.info(f"Converting script to speech: {script_url}")
        
        # Download script from GCS
        try:
            script_text = storage_manager.download_as_text(script_url)
            logger.info(f"Downloaded script: {len(script_text)} characters")
        except Exception as e:
            raise Exception(f"Failed to download script from {script_url}: {str(e)}")
        
        # Initialize TTS client
        client = texttospeech.TextToSpeechClient()
        
        # Prepare synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=script_text)
        
        # Configure voice selection - use default high-quality voice
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Journey-F",  # High-quality neural voice
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Configure audio output with default settings
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,  # Normal speed
            pitch=0.0,
            volume_gain_db=0.0,
            sample_rate_hertz=settings.AUDIO_SAMPLE_RATE
        )
        
        # Perform text-to-speech synthesis
        logger.info("Synthesizing speech...")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Calculate approximate duration (rough estimate)
        word_count = len(script_text.split())
        estimated_duration = word_count / 150  # 150 WPM at normal speed
        
        # Generate unique filename for audio
        audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
        
        # Upload audio to Google Cloud Storage
        upload_result = storage_manager.upload_binary(
            content=response.audio_content,
            folder="audio",
            filename=audio_filename,
            content_type="audio/mpeg"
        )
        
        if upload_result["status"] != "success":
            raise Exception(f"Failed to upload audio: {upload_result.get('error', 'Unknown error')}")
        
        # Voice used is always the default
        voice_used = "en-US-Journey-F"
        
        logger.info(f"Successfully generated audio: {len(response.audio_content)} bytes, ~{estimated_duration:.1f}s")
        
        return {
            "audio_url": upload_result["gcs_url"],
            "public_url": upload_result["public_url"],
            "duration": estimated_duration,
            "voice_used": voice_used,
            "speaking_rate": 1.0,
            "audio_config": {
                "encoding": "MP3",
                "sample_rate": settings.AUDIO_SAMPLE_RATE,
                "speaking_rate": 1.0
            },
            "script_url": script_url,
            "filename": audio_filename,
            "audio_size_bytes": len(response.audio_content),
            "status": "success"
        }
        
    except Exception as e:
        error_msg = f"Failed to convert script to speech: {str(e)}"
        logger.error(error_msg)
        
        return {
            "script_url": script_url,
            "error": error_msg,
            "status": "failed"
        }

def get_available_voices(language_code: str = "en-US") -> Dict[str, Any]:
    """
    Get list of available voices for a given language.
    
    Args:
        language_code (str): Language code (e.g., 'en-US')
        
    Returns:
        Dict[str, Any]: Available voices and their properties
    """
    try:
        client = texttospeech.TextToSpeechClient()
        
        # List available voices
        voices = client.list_voices(language_code=language_code)
        
        voice_list = []
        for voice in voices.voices:
            voice_info = {
                "name": voice.name,
                "language_codes": list(voice.language_codes),
                "ssml_gender": voice.ssml_gender.name,
                "natural_sample_rate_hertz": voice.natural_sample_rate_hertz
            }
            voice_list.append(voice_info)
        
        return {
            "language_code": language_code,
            "voices": voice_list,
            "count": len(voice_list),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "language_code": language_code,
            "error": str(e),
            "status": "failed"
        }

def validate_audio_settings(speaking_rate: float, pitch: float = 0.0, volume_gain_db: float = 0.0) -> Dict[str, Any]:
    """
    Validate audio synthesis settings.
    
    Args:
        speaking_rate (float): Speaking rate (0.25 to 4.0)
        pitch (float): Pitch adjustment (-20.0 to 20.0)
        volume_gain_db (float): Volume gain in dB (-96.0 to 16.0)
        
    Returns:
        Dict[str, Any]: Validation results
    """
    issues = []
    
    if not (0.25 <= speaking_rate <= 4.0):
        issues.append(f"Speaking rate {speaking_rate} is out of range (0.25-4.0)")
    
    if not (-20.0 <= pitch <= 20.0):
        issues.append(f"Pitch {pitch} is out of range (-20.0 to 20.0)")
    
    if not (-96.0 <= volume_gain_db <= 16.0):
        issues.append(f"Volume gain {volume_gain_db} is out of range (-96.0 to 16.0)")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "settings": {
            "speaking_rate": speaking_rate,
            "pitch": pitch,
            "volume_gain_db": volume_gain_db
        }
    }

# Create the ADK FunctionTool
tts_tool = FunctionTool(func=text_to_speech)

# Export additional functions for use by other modules
__all__ = ["tts_tool", "text_to_speech", "get_available_voices", "validate_audio_settings"] 