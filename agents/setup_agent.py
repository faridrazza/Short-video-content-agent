"""
Setup Agent for the Multi-Agent Video Generation System.
Initializes storage, authentication, and validates system configuration.
"""

from google.adk.agents import LlmAgent
from tools.storage_setup_tool import storage_setup_tool, bucket_info_tool, env_setup_tool

# Setup Agent - Initializes the system
setup_agent = LlmAgent(
    name="SystemSetup",
    model="gemini-2.0-flash",
    instruction="""You are a system setup agent responsible for initializing the video generation pipeline.

Your tasks:
1. Create .env file if missing using create_env_file()
2. Setup GCS bucket using setup_storage_bucket() 
3. Get bucket information using get_bucket_info()
4. Provide setup instructions to the user

Always run these tools in order and provide clear instructions for any manual steps needed.""",
    description="Initializes storage and system configuration for video generation",
    tools=[storage_setup_tool, bucket_info_tool, env_setup_tool],
    output_key="setup_data"
) 