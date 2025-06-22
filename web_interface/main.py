"""
Main Web Interface for the Multi-Agent Video Generation System.
FastAPI application using ADK integration for agent orchestration.
"""

import os
import logging
import uvicorn
from pathlib import Path
from google.adk.cli.fast_api import get_fast_api_app
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_app():
    """
    Create and configure the FastAPI application with ADK integration.
    
    Returns:
        FastAPI: Configured application instance
    """
    try:
        # Get the directory containing the agents
        current_dir = Path(__file__).parent
        agents_dir = current_dir.parent / "agents"
        
        logger.info(f"Agents directory: {agents_dir}")
        logger.info(f"Google Cloud Project: {settings.GOOGLE_CLOUD_PROJECT}")
        
        # Validate that agents directory exists
        if not agents_dir.exists():
            raise FileNotFoundError(f"Agents directory not found: {agents_dir}")
        
        # Check for agent.py file
        agent_file = agents_dir / "agent.py"
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_file}")
        
        # Configure session service URI
        session_service_uri = "sqlite:///./sessions.db"
        if settings.GOOGLE_CLOUD_PROJECT:
            # Use Cloud SQL or Firestore in production
            session_service_uri = f"sqlite:///./sessions_{settings.GOOGLE_CLOUD_PROJECT}.db"
        
        # Create FastAPI app with ADK integration
        app = get_fast_api_app(
            agents_dir=str(agents_dir),
            session_service_uri=session_service_uri,
            allow_origins=["*"],  # Configure CORS for development
            web=True,  # Enable ADK web UI
            title="Multi-Agent Video Generation System",
            description="AI-powered video generation using Google Cloud and ADK",
            version="1.0.0"
        )
        
        # Add custom middleware and routes if needed
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "video-generation-agent",
                "version": "1.0.0",
                "agents_dir": str(agents_dir),
                "google_cloud_project": settings.GOOGLE_CLOUD_PROJECT
            }
        
        @app.get("/config")
        async def get_system_config():
            """Get system configuration information."""
            from agents.agent import get_agent_config, validate_agent_system
            
            config = get_agent_config()
            validation = validate_agent_system()
            
            return {
                "system_config": config,
                "validation": validation,
                "settings": {
                    "project": settings.GOOGLE_CLOUD_PROJECT,
                    "location": settings.GOOGLE_CLOUD_LOCATION,
                    "bucket": settings.GCS_BUCKET_NAME,
                    "resolution": settings.DEFAULT_VIDEO_RESOLUTION,
                    "fps": settings.DEFAULT_FPS
                }
            }
        
        logger.info("FastAPI application created successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create FastAPI application: {e}")
        raise

# Create the application instance
app = create_app()

def main():
    """
    Main entry point for the web application.
    """
    try:
        # Validate required environment variables
        missing_settings = settings.validate_required_settings()
        if missing_settings and not settings.DEBUG:
            logger.error(f"Missing required environment variables: {', '.join(missing_settings)}")
            logger.error("Please set the required environment variables before starting the application.")
            return
        
        # Get port from environment
        port = int(os.environ.get("PORT", 8080))
        host = "0.0.0.0"
        
        logger.info(f"Starting Multi-Agent Video Generation System on {host}:{port}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        logger.info(f"Google Cloud Project: {settings.GOOGLE_CLOUD_PROJECT}")
        
        # Configure uvicorn settings
        uvicorn_config = {
            "host": host,
            "port": port,
            "log_level": settings.LOG_LEVEL.lower(),
            "reload": settings.DEBUG,  # Enable auto-reload in debug mode
            "access_log": True
        }
        
        # Start the server
        uvicorn.run(app, **uvicorn_config)
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

if __name__ == "__main__":
    main() 