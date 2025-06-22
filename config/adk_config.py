"""
ADK Configuration Module
Sets environment variables before any other imports to ensure ADK agents have access to credentials.
"""

import os

# Set environment variables directly for ADK agents
os.environ.update({
    'GOOGLE_CLOUD_PROJECT': 'educationalai-446710',
    'GOOGLE_APPLICATION_CREDENTIALS': './service-account-key.json.json',
    'GCS_BUCKET_NAME': 'educationalai-446710-video-gen',
    'GEMINI_API_KEY': 'AIzaSyD8FLr6Tz3amiK10nL7ctXjOe5nI-i8Wa4',
    'GOOGLE_API_KEY': 'AIzaSyD8FLr6Tz3amiK10nL7ctXjOe5nI-i8Wa4',
    'GOOGLE_GENAI_USE_VERTEXAI': 'False',
    'DEBUG': 'True',
    'LOG_LEVEL': 'INFO'
})

# Verify environment variables are set
required_vars = ['GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS', 'GCS_BUCKET_NAME', 'GEMINI_API_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} is not set") 