"""Configuration module for the Multi-Agent Video Generation System."""

# Import ADK config first to set environment variables
from . import adk_config
from .settings import settings, Settings
 
__all__ = ["settings", "Settings"] 