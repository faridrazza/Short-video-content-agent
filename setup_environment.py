#!/usr/bin/env python3
"""
Environment Setup Script for Multi-Agent Video Generation System.
Run this script to initialize your system for video generation.
"""

import os
import sys
import subprocess
import uuid
from pathlib import Path

def print_header():
    """Print setup header."""
    print("=" * 60)
    print("🎬 Multi-Agent Video Generation System Setup")
    print("=" * 60)
    print()

def check_python_version():
    """Check Python version compatibility."""
    print("📋 Checking Python version...")
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is compatible")
    print()

def check_gcloud_cli():
    """Check if gcloud CLI is installed."""
    print("📋 Checking Google Cloud CLI...")
    try:
        result = subprocess.run(['gcloud', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Google Cloud CLI is installed")
            return True
        else:
            print("❌ Google Cloud CLI not found")
            return False
    except FileNotFoundError:
        print("❌ Google Cloud CLI not found")
        return False

def create_env_file():
    """Create .env file with proper configuration."""
    print("📋 Creating .env file...")
    
    if os.path.exists(".env"):
        print("⚠️  .env file already exists. Backing up to .env.backup")
        os.rename(".env", ".env.backup")
    
    # Generate unique bucket name
    project_id = input("Enter your Google Cloud Project ID: ").strip()
    if not project_id:
        project_id = "your-project-id"
    
    bucket_name = f"video-gen-{uuid.uuid4().hex[:8]}"
    
    env_content = f"""# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT={project_id}
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=True

# Storage Configuration
GCS_BUCKET_NAME={bucket_name}

# API Keys (Update these with your actual keys)
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
    
    print(f"✅ Created .env file with bucket name: {bucket_name}")
    print()
    return project_id, bucket_name

def install_dependencies():
    """Install required Python packages."""
    print("📋 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False
    print()
    return True

def authenticate_gcloud():
    """Guide user through gcloud authentication."""
    print("📋 Setting up Google Cloud authentication...")
    
    print("Please run the following commands manually:")
    print("1. Authenticate with Google Cloud:")
    print("   gcloud auth login")
    print("2. Set up application default credentials:")
    print("   gcloud auth application-default login")
    print("3. Set your default project:")
    print("   gcloud config set project YOUR_PROJECT_ID")
    print()
    
    input("Press Enter after completing the authentication steps...")
    print()

def enable_apis():
    """Guide user to enable required Google Cloud APIs."""
    print("📋 Required Google Cloud APIs:")
    apis = [
        "storage-api.googleapis.com",
        "texttospeech.googleapis.com",
        "run.googleapis.com",
        "aiplatform.googleapis.com"
    ]
    
    print("Please enable these APIs in your Google Cloud project:")
    for api in apis:
        print(f"   - {api}")
    
    print("\nYou can enable them with:")
    for api in apis:
        print(f"   gcloud services enable {api}")
    
    print()
    input("Press Enter after enabling the APIs...")
    print()

def create_test_script():
    """Create a test script to verify setup."""
    test_content = '''#!/usr/bin/env python3
"""Test script to verify the setup."""

def test_setup():
    """Test the system setup."""
    print("🧪 Testing Multi-Agent Video Generation System Setup")
    print("=" * 50)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from agents.agent import root_agent
        from tools.storage_setup_tool import setup_storage_bucket
        print("✅ All imports successful")
        
        # Test agent configuration
        print("🤖 Testing agent configuration...")
        print(f"   Root agent: {root_agent.name}")
        print(f"   Sub-agents: {len(root_agent.sub_agents)}")
        print("✅ Agent configuration OK")
        
        # Test storage setup
        print("💾 Testing storage setup...")
        result = setup_storage_bucket()
        if result.get("status") == "success":
            print("✅ Storage setup successful")
            print(f"   Bucket: {result.get('bucket_name')}")
        else:
            print(f"❌ Storage setup failed: {result.get('error')}")
        
        print("\\n🎉 Setup test completed!")
        
    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    test_setup()
'''
    
    with open("test_setup.py", "w") as f:
        f.write(test_content)
    
    print("✅ Created test_setup.py script")
    print()

def main():
    """Main setup function."""
    print_header()
    
    # Check prerequisites
    check_python_version()
    gcloud_available = check_gcloud_cli()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed during dependency installation")
        sys.exit(1)
    
    # Create environment file
    project_id, bucket_name = create_env_file()
    
    # Guide through authentication if gcloud is available
    if gcloud_available:
        authenticate_gcloud()
        enable_apis()
    else:
        print("⚠️  Google Cloud CLI not found. Please install it from:")
        print("   https://cloud.google.com/sdk/docs/install")
        print()
    
    # Create test script
    create_test_script()
    
    # Final instructions
    print("🎯 Setup Instructions:")
    print("1. Update .env file with your actual API keys:")
    print("   - GEMINI_API_KEY: Get from https://aistudio.google.com/app/apikey")
    print("   - HF_API_TOKEN: Get from https://huggingface.co/settings/tokens")
    print()
    print("2. If using Google Cloud, ensure you're authenticated:")
    print("   gcloud auth application-default login")
    print()
    print("3. Test your setup by running:")
    print("   python test_setup.py")
    print()
    print("4. Start the video generation system:")
    print("   adk web")
    print()
    print("✅ Setup completed! Your system is ready for video generation.")

if __name__ == "__main__":
    main() 