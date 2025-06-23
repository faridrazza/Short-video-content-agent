"""
Main Agent Implementation for the Multi-Agent Video Generation System.
Orchestrates the complete video generation pipeline using ADK agents.
"""

import logging
import sys
import os

# Add the parent directory to the Python path so we can import from tools and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
    from tools.script_tool import script_tool
    from tools.tts_tool import tts_tool
    from tools.prompt_tool import prompt_tool
    from tools.image_tool import image_tool
    from tools.assembly_tool import assembly_tool
    from config.settings import settings
except ImportError as e:
    # Fallback for when config.settings is not available
    print(f"Import error: {e}")
    
    # Create a basic settings object as fallback
    class BasicSettings:
        GEMINI_MODEL = "gemini-2.0-flash"
        LOG_LEVEL = "INFO"
        DEFAULT_VIDEO_RESOLUTION = (1024, 576)
    
    settings = BasicSettings()
    
    # Try importing just the ADK and tools
    from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
    from tools.script_tool import script_tool
    from tools.tts_tool import tts_tool
    from tools.prompt_tool import prompt_tool
    from tools.image_tool import image_tool
    from tools.assembly_tool import assembly_tool

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))

# Define individual specialized LLM agents
script_agent = LlmAgent(
    name="ScriptGenerator",
    model=settings.GEMINI_MODEL,
    instruction="""You are a professional video script writer. Use the generate_script tool to create engaging, 
    visual video scripts from topics. Focus on content that can be easily illustrated with images. 
    Keep scripts concise but compelling, suitable for 30-60 second videos.""",
    description="Creates engaging video scripts from input topics using AI",
    tools=[script_tool],
    output_key="script_data"
)

tts_agent = LlmAgent(
    name="AudioNarrator",
    model=settings.GEMINI_MODEL,
    instruction="""You are an audio production specialist. Use the text_to_speech tool to convert scripts 
    into high-quality audio narration. Use the script_url from the session state to access the script content.
    Select appropriate voice settings for professional narration.""",
    description="Converts script text to professional audio narration",
    tools=[tts_tool],
    output_key="audio_data"
)

prompt_agent = LlmAgent(
    name="PromptGenerator", 
    model=settings.GEMINI_MODEL,
    instruction="""You are a visual storytelling expert and prompt engineer. Use the generate_prompts tool 
    to create detailed, cinematic image generation prompts from the script text in session state. 
    Focus on creating 8 visually striking scenes that tell the story effectively.""",
    description="Creates detailed image generation prompts from scripts",
    tools=[prompt_tool],
    output_key="prompts_data"
)

image_agent = LlmAgent(
    name="ImageCreator",
    model=settings.GEMINI_MODEL,
    instruction="""You are a digital artist and image generation specialist. Use the generate_images tool 
    to create high-quality images from the prompts in session state. Ensure images are optimized for 
    video production with consistent quality and style.""",
    description="Generates high-quality images from descriptive prompts",
    tools=[image_tool],
    output_key="images_data"
)

assembly_agent = LlmAgent(
    name="VideoAssembler",
    model=settings.GEMINI_MODEL,
    instruction="""You are a video production specialist. Your job is to combine all the assets created by previous agents into a final video.

IMPORTANT: You must use the assemble_video tool to create the final video. Here's how to extract the required parameters from the session state:

1. audio_url: Look for audio_data in session state, then get the "audio_url" or "gcs_url" field
2. images_data: Look for images_data in session state and pass the entire JSON object as a string
3. script_url: Look for script_data in session state, then get the "script_url" field (optional)

Example of how to call the tool:
- If session state has audio_data with audio_url "gs://bucket/audio.mp3"
- And images_data with a JSON object containing image information
- And optionally script_data with script_url
Then call: assemble_video(audio_url="gs://bucket/audio.mp3", images_data="{...json string...}", script_url="gs://bucket/script.txt")

You MUST call the assemble_video tool to complete the video generation process.""",
    description="Combines audio, images, and text into final video production",
    tools=[assembly_tool],
    output_key="final_video"
)

# Create parallel processing stage for TTS and Prompt generation
# This allows both audio and visual prompt generation to happen simultaneously
parallel_stage = ParallelAgent(
    name="ParallelProcessing",
    sub_agents=[tts_agent, prompt_agent],
    description="Processes audio narration and image prompts simultaneously for efficiency"
)

# Main sequential pipeline orchestrating the complete video generation workflow
root_agent = SequentialAgent(
    name="VideoGenerationPipeline",
    sub_agents=[
        script_agent,      # Step 1: Generate script from topic
        parallel_stage,    # Step 2: Generate audio AND prompts in parallel
        image_agent,       # Step 3: Generate images from prompts
        assembly_agent     # Step 4: Assemble final video
    ],
    description="""Complete multi-agent video generation workflow that transforms a topic into a 
    professional video. The pipeline includes script generation, parallel audio and prompt creation, 
    image generation, and final video assembly with captions and transitions."""
)

# Agent configuration for different use cases
def get_agent_config() -> dict:
    """
    Get configuration information for the agent system.
    
    Returns:
        dict: Agent system configuration
    """
    return {
        "pipeline_name": "VideoGenerationPipeline",
        "total_agents": 4,
        "parallel_stages": 1,
        "estimated_time_minutes": "2-4",
        "supported_formats": ["MP4"],
        "max_video_duration": "60 seconds",
        "resolution": f"{getattr(settings, 'DEFAULT_VIDEO_RESOLUTION', (1024, 576))[0]}x{getattr(settings, 'DEFAULT_VIDEO_RESOLUTION', (1024, 576))[1]}",
        "agents": {
            "script_generator": {
                "name": script_agent.name,
                "description": script_agent.description,
                "tools": ["generate_script"]
            },
            "audio_narrator": {
                "name": tts_agent.name,
                "description": tts_agent.description,
                "tools": ["text_to_speech"]
            },
            "prompt_generator": {
                "name": prompt_agent.name,
                "description": prompt_agent.description,
                "tools": ["generate_prompts"]
            },
            "image_creator": {
                "name": image_agent.name,
                "description": image_agent.description,
                "tools": ["generate_images"]
            },
            "video_assembler": {
                "name": assembly_agent.name,
                "description": assembly_agent.description,
                "tools": ["assemble_video"]
            }
        },
        "workflow": [
            "1. Script Generation (from topic)",
            "2. Parallel Processing:",
            "   - Audio Narration (from script)",
            "   - Image Prompts (from script)",
            "3. Image Generation (from prompts)",
            "4. Video Assembly (combine all assets)"
        ]
    }

def validate_agent_system() -> dict:
    """
    Validate that the agent system is properly configured.
    
    Returns:
        dict: Validation results
    """
    issues = []
    
    # Check that all agents are properly configured
    agents_to_check = [script_agent, tts_agent, prompt_agent, image_agent, assembly_agent]
    
    for agent in agents_to_check:
        if not agent.name:
            issues.append(f"Agent missing name: {agent}")
        if not agent.tools:
            issues.append(f"Agent {agent.name} has no tools")
        if not agent.instruction:
            issues.append(f"Agent {agent.name} missing instruction")
    
    # Check parallel agent configuration
    if len(parallel_stage.sub_agents) != 2:
        issues.append("Parallel stage should have exactly 2 agents")
    
    # Check root agent configuration
    if len(root_agent.sub_agents) != 4:
        issues.append("Root agent should have exactly 4 sub-agents")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "agent_count": len(agents_to_check),
        "parallel_agents": len(parallel_stage.sub_agents),
        "total_stages": len(root_agent.sub_agents)
    }

# Export the root agent and utility functions
__all__ = ["root_agent", "get_agent_config", "validate_agent_system"] 