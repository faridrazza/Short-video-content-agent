"""
Configuration settings for the Multi-Agent Video Generation System.
Handles environment variables and system configuration.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# Try env.local first (for local development), then fall back to .env
load_dotenv('env.local')
load_dotenv()  # This will load .env if it exists, but won't override existing variables

class Settings:
    """Configuration settings for the video generation system."""
    
    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GOOGLE_GENAI_USE_VERTEXAI: bool = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() == "true"
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
    HUGGINGFACE_API_KEY: str = os.getenv("HF_API_TOKEN", "")  # Alias for compatibility
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY", "") or os.getenv("TOGETHER_API", "")  # Try both keys
    
    # Storage Configuration
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    
    # Video Generation Settings
    DEFAULT_VIDEO_RESOLUTION: tuple = (1024, 576)  # 16:9 aspect ratio
    DEFAULT_VIDEO_FPS: int = 24
    MAX_SCRIPT_LENGTH: int = 500  # characters
    AUDIO_SAMPLE_RATE: int = 16000
    
    # Image Generation Settings
    DEFAULT_IMAGE_SIZE: tuple = (1024, 576)  # 16:9 aspect ratio for video
    IMAGE_GENERATION_SERVICE: str = os.getenv("IMAGE_GENERATION_SERVICE", "togetherai")
    LOCAL_SD_URL: str = os.getenv("LOCAL_SD_URL", "http://localhost:7860")
    
    # Development Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Model Configuration
    GEMINI_MODEL: str = "gemini-2.0-flash"
    STABLE_DIFFUSION_API_URL: str = os.getenv("STABLE_DIFFUSION_API_URL", "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5")
    
    # Together AI Configuration
    FLUX_MODEL_ENDPOINT: str = os.getenv("FLUX_MODEL_ENDPOINT", "black-forest-labs/FLUX.1-schnell-Free")
    
    @classmethod
    def validate_required_settings(cls) -> list[str]:
        """Validate that all required settings are present."""
        missing_settings = []
        
        required_settings = [
            ("GOOGLE_CLOUD_PROJECT", cls.GOOGLE_CLOUD_PROJECT),
            ("GEMINI_API_KEY", cls.GEMINI_API_KEY),
            ("GCS_BUCKET_NAME", cls.GCS_BUCKET_NAME),
        ]
        
        for setting_name, setting_value in required_settings:
            if not setting_value:
                missing_settings.append(setting_name)
        
        return missing_settings
    
    @classmethod
    def get_gcs_bucket_url(cls, path: str = "") -> str:
        """Generate GCS bucket URL for a given path."""
        base_url = f"gs://{cls.GCS_BUCKET_NAME}"
        return f"{base_url}/{path}" if path else base_url
    
    @classmethod
    def get_public_gcs_url(cls, path: str) -> str:
        """Generate public GCS URL for a given path."""
        return f"https://storage.googleapis.com/{cls.GCS_BUCKET_NAME}/{path}"

# Global settings instance
settings = Settings()

# Only validate in production (not debug mode)
missing_settings = settings.validate_required_settings()
if missing_settings and not settings.DEBUG:
    print(f"Warning: Missing required environment variables: {', '.join(missing_settings)}")
    # Don't raise error, just warn 