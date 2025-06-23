"""
ADK Configuration Module
Sets environment variables before any other imports to ensure ADK agents have access to credentials.
"""

import os

# Load environment variables from .env files instead of hardcoding
from dotenv import load_dotenv
load_dotenv('env.local')
load_dotenv()

# Set environment variables from loaded values (no hardcoded secrets)
import os
os.environ.update({
    'GOOGLE_CLOUD_PROJECT': os.getenv('GOOGLE_CLOUD_PROJECT', ''),
    'GOOGLE_APPLICATION_CREDENTIALS': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', ''),
    'GCS_BUCKET_NAME': os.getenv('GCS_BUCKET_NAME', ''),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', ''),
    'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
    'GOOGLE_GENAI_USE_VERTEXAI': os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'False'),
    'DEBUG': os.getenv('DEBUG', 'True'),
    'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO')
})

# Verify environment variables are set
required_vars = ['GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS', 'GCS_BUCKET_NAME', 'GEMINI_API_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} is not set") 