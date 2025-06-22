"""
Storage Setup Tool for the Multi-Agent Video Generation System.
Creates and configures Google Cloud Storage bucket for storing video assets.
"""

import logging
import os
from typing import Dict, Any
from google.adk.tools import FunctionTool
from google.cloud import storage
from google.cloud.exceptions import Conflict
from config.settings import settings

logger = logging.getLogger(__name__)

def setup_storage_bucket() -> Dict[str, Any]:
    """
    Create and configure the GCS bucket for video generation.
    
    Returns:
        Dict[str, Any]: Contains bucket info and setup status
    """
    try:
        logger.info("Setting up GCS bucket for video generation")
        
        # Initialize GCS client
        client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        
        bucket_name = settings.GCS_BUCKET_NAME or "video-generation-assets"
        
        # Try to get existing bucket first
        try:
            bucket = client.bucket(bucket_name)
            bucket.reload()  # Test if bucket exists and we have access
            logger.info(f"Using existing bucket: {bucket_name}")
            bucket_created = False
        except Exception:
            # Bucket doesn't exist or no access, create new one
            logger.info(f"Creating new bucket: {bucket_name}")
            bucket = client.bucket(bucket_name)
            bucket = client.create_bucket(bucket, location=settings.GOOGLE_CLOUD_LOCATION)
            bucket_created = True
        
        # Set up bucket for public read access for generated videos
        try:
            policy = bucket.get_iam_policy(requested_policy_version=3)
            policy.bindings.append({
                "role": "roles/storage.objectViewer",
                "members": {"allUsers"}
            })
            bucket.set_iam_policy(policy)
            logger.info("Configured bucket for public read access")
        except Exception as e:
            logger.warning(f"Could not set public access: {e}")
        
        # Create folder structure
        folders = ["scripts", "audio", "prompts", "images", "videos"]
        for folder in folders:
            try:
                # Create a placeholder file in each folder to ensure they exist
                blob = bucket.blob(f"{folder}/.gitkeep")
                blob.upload_from_string("")
            except Exception as e:
                logger.warning(f"Could not create folder {folder}: {e}")
        
        logger.info(f"Successfully set up storage bucket: {bucket_name}")
        
        return {
            "bucket_name": bucket_name,
            "bucket_url": f"gs://{bucket_name}",
            "public_base_url": f"https://storage.googleapis.com/{bucket_name}",
            "location": bucket.location,
            "created": bucket_created,
            "folders_created": folders,
            "status": "success"
        }
        
    except Exception as e:
        error_msg = f"Failed to setup storage bucket: {str(e)}"
        logger.error(error_msg)
        
        return {
            "error": error_msg,
            "status": "failed"
        }

def get_bucket_info() -> Dict[str, Any]:
    """
    Get information about the current GCS bucket.
    
    Returns:
        Dict[str, Any]: Bucket information and statistics
    """
    try:
        client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        bucket_name = settings.GCS_BUCKET_NAME
        
        if not bucket_name:
            return {
                "error": "No bucket name configured",
                "status": "failed"
            }
        
        bucket = client.bucket(bucket_name)
        bucket.reload()
        
        # Get blob count and sizes for each folder
        folder_stats = {}
        folders = ["scripts", "audio", "prompts", "images", "videos"]
        
        for folder in folders:
            blobs = list(bucket.list_blobs(prefix=f"{folder}/"))
            total_size = sum(blob.size or 0 for blob in blobs)
            folder_stats[folder] = {
                "count": len(blobs),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        
        return {
            "bucket_name": bucket_name,
            "bucket_url": f"gs://{bucket_name}",
            "location": bucket.location,
            "created": bucket.time_created.isoformat() if bucket.time_created else None,
            "folder_stats": folder_stats,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

def create_env_file() -> Dict[str, Any]:
    """
    Create a .env file with proper configuration for the system.
    
    Returns:
        Dict[str, Any]: Creation status and instructions
    """
    try:
        # Check if .env already exists
        if os.path.exists(".env"):
            logger.info(".env file already exists")
            return {
                "message": ".env file already exists",
                "status": "exists"
            }
        
        # Generate a unique bucket name if not provided
        import uuid
        project_id = settings.GOOGLE_CLOUD_PROJECT or "your-project-id"
        default_bucket = f"video-gen-{uuid.uuid4().hex[:8]}"
        
        env_content = f"""# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT={project_id}
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=True

# Storage Configuration
GCS_BUCKET_NAME={default_bucket}

# API Keys (Replace with your actual keys)
GEMINI_API_KEY=your-gemini-api-key-here
HF_API_TOKEN=your-huggingface-token-here

# Optional: Image Generation Service
IMAGE_GENERATION_SERVICE=huggingface
STABLE_DIFFUSION_API_URL=https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0

# Development Settings
DEBUG=True
LOG_LEVEL=INFO
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        logger.info("Created .env file with default configuration")
        
        return {
            "env_file_path": ".env",
            "bucket_name": default_bucket,
            "message": "Created .env file with default configuration. Please update with your actual API keys.",
            "next_steps": [
                "Update GEMINI_API_KEY with your actual Gemini API key",
                "Update HF_API_TOKEN with your Hugging Face token",
                "Run setup_storage_bucket() to create the GCS bucket",
                "Authenticate with: gcloud auth application-default login"
            ],
            "status": "success"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

# Create the ADK FunctionTools
storage_setup_tool = FunctionTool(func=setup_storage_bucket)
bucket_info_tool = FunctionTool(func=get_bucket_info)
env_setup_tool = FunctionTool(func=create_env_file)

# Export functions
__all__ = ["storage_setup_tool", "bucket_info_tool", "env_setup_tool", "setup_storage_bucket", "get_bucket_info", "create_env_file"] 