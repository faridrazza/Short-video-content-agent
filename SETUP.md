# Multi-Agent Video Generation System - Complete Setup Guide

## 🚀 **Quick Start Checklist**

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] Google Cloud Project set up
- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] System tested and running

## 📋 **Prerequisites**

### **1. Python Installation (Windows)**

Since Python wasn't found on your system, install it first:

**Option A: Microsoft Store (Recommended)**
```bash
# Open Microsoft Store and search for "Python 3.12"
# Install the latest Python version
```

**Option B: Official Python.org**
1. Download from: https://www.python.org/downloads/
2. Install with "Add Python to PATH" checked
3. Verify installation: `python --version`

### **2. Google Cloud Account Setup**
- Google Cloud Project with billing enabled
- $100 credits available via contest form: https://docs.google.com/forms/d/e/1FAIpQLSeqzYFwqW5IyHD4wipyDxMrs1Idr91Up7S4PQO1ue058oYuTg/viewform

## 🛠️ **Step-by-Step Setup**

### **Step 1: Virtual Environment Setup**

```bash
# Navigate to your project directory
cd C:\Users\moham\short-video-generation-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate.bat

# Verify activation (should show venv in prompt)
where python
```

### **Step 2: Install Dependencies**

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install all project dependencies
pip install -r requirements.txt

# Verify ADK installation
python -c "import google.adk; print('ADK installed successfully')"
```

### **Step 3: Google Cloud Setup**

#### **A. Install Google Cloud CLI**
```bash
# Download and install from: https://cloud.google.com/sdk/docs/install
# Or use PowerShell:
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe
```

#### **B. Initialize Google Cloud**
```bash
# Initialize gcloud (this will open browser for authentication)
gcloud init

# Set your project (replace with your actual project ID)
gcloud config set project your-project-id

# Enable required APIs
gcloud services enable storage-api.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Set up Application Default Credentials
gcloud auth application-default login
```

#### **C. Create GCS Bucket**
```bash
# Create bucket for video assets (replace with unique name)
gsutil mb gs://your-unique-bucket-name

# Set bucket permissions (for development only)
gsutil iam ch allUsers:objectViewer gs://your-unique-bucket-name
```

### **Step 4: Environment Configuration**

#### **A. Copy Environment Template**
```bash
# Copy the example file
copy env.example .env
```

#### **B. Configure Required Variables**

Edit `.env` file with your actual values:

```env
# REQUIRED - Your Google Cloud Project
GOOGLE_CLOUD_PROJECT=your-actual-project-id

# REQUIRED - Your region
GOOGLE_CLOUD_LOCATION=us-central1

# REQUIRED - Use Vertex AI (recommended)
GOOGLE_GENAI_USE_VERTEXAI=True

# REQUIRED - Your GCS bucket
GCS_BUCKET_NAME=your-unique-bucket-name

# REQUIRED - Hugging Face token for image generation
HF_API_TOKEN=your-huggingface-token

# OPTIONAL - Gemini API key (only if not using Vertex AI)
GEMINI_API_KEY=your-gemini-api-key

# Development settings
DEBUG=True
LOG_LEVEL=INFO
```

### **Step 5: Get API Keys**

#### **A. Hugging Face Token (REQUIRED)**
1. Go to: https://huggingface.co/settings/tokens
2. Create new token with "Read" permissions
3. Copy token to `HF_API_TOKEN` in `.env`

#### **B. Gemini API Key (Optional)**
1. Go to: https://aistudio.google.com/apikey
2. Create new API key
3. Copy to `GEMINI_API_KEY` in `.env` (only if using Google AI Studio instead of Vertex AI)

## 🧪 **Testing Your Setup**

### **Step 1: Validate Configuration**
```bash
# Test environment variables
python -c "from config.settings import settings; print('✅ Settings loaded successfully')"

# Test Google Cloud authentication
python -c "from google.cloud import storage; client = storage.Client(); print('✅ GCS authentication working')"

# Test ADK import
python -c "from agents.agent import validate_agent_system; print(validate_agent_system())"
```

### **Step 2: Run System Tests**
```bash
# Run unit tests
python -m pytest tests/ -v

# Test specific tool
python -c "from tools.script_tool import generate_script; print(generate_script('AI technology'))"
```

### **Step 3: Start the Application**

#### **Option A: Web Interface (Recommended)**
```bash
# Start FastAPI web interface
python -m web_interface.main

# Access at: http://localhost:8080
```

#### **Option B: ADK CLI**
```bash
# Start ADK web UI
adk web

# Access at: http://localhost:8000
```

#### **Option C: Direct Agent Execution**
```bash
# Run agent directly
adk run ./agents
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **1. Python Not Found**
```bash
# Check if Python is in PATH
where python
where python3

# If not found, reinstall Python with "Add to PATH" option
```

#### **2. Virtual Environment Issues**
```bash
# Deactivate and recreate
deactivate
rmdir /s venv
python -m venv venv
venv\Scripts\Activate.ps1
```

#### **3. Google Cloud Authentication**
```bash
# Clear and reset credentials
gcloud auth revoke --all
gcloud auth login
gcloud auth application-default login
```

#### **4. Missing Dependencies**
```bash
# Force reinstall all dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt --force-reinstall
```

#### **5. Environment Variables Not Loading**
```bash
# Check .env file exists and has correct format
cat .env  # Linux/Mac
type .env  # Windows

# Verify loading
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GOOGLE_CLOUD_PROJECT'))"
```

## 🎯 **Verification Checklist**

After setup, verify these work:

- [ ] `python --version` shows Python 3.10+
- [ ] Virtual environment is activated (shows in prompt)
- [ ] `pip list` shows `google-adk` installed
- [ ] `gcloud config list` shows your project
- [ ] `.env` file has all required variables
- [ ] `python -c "from config.settings import settings; print(settings.GOOGLE_CLOUD_PROJECT)"` works
- [ ] Web interface starts without errors
- [ ] Can generate a test script: "What is AI?"

## 🚀 **Next Steps**

Once setup is complete:

1. **Test the full pipeline**: Generate a video from "Artificial Intelligence"
2. **Check GCS bucket**: Verify assets are being stored
3. **Monitor logs**: Watch for any errors in the console
4. **Explore the web UI**: Test different video topics
5. **Review generated videos**: Check quality and timing

## 📚 **Additional Resources**

- **ADK Documentation**: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/develop/adk
- **Contest Guidelines**: See `contestfile` in project root
- **Google Cloud Setup**: https://cloud.google.com/docs/get-started
- **Hugging Face Tokens**: https://huggingface.co/docs/hub/security-tokens

## 🔐 **Security Notes**

- Never commit `.env` file to version control
- Use service accounts for production deployment
- Rotate API keys regularly
- Set proper GCS bucket permissions for production
- Use Google Cloud Secret Manager for sensitive data in production

---

**Need Help?** Check the troubleshooting section above or review the project's README.md for additional guidance. 