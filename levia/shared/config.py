"""Configuration utilities for agents.

Simplified for Google ADK - focuses on external service configuration only.
Agent-to-agent communication is handled by A2A SDK.
"""
import os
import logging

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='[%(name)s] %(asctime)s - %(levelname)s - %(message)s'
)


def get_elasticsearch_url() -> str:
    """Get Elasticsearch URL from environment."""
    return os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")


def get_gemini_api_key() -> str:
    """Get Gemini API key from environment."""
    return os.getenv("GEMINI_API_KEY", "")


def get_google_project_id() -> str:
    """Get Google Cloud project ID from environment."""
    return os.getenv("GOOGLE_CLOUD_PROJECT", "")


def get_public_url(default_port: int = 8000) -> str:
    """Get public URL for A2A agent card."""
    return os.getenv("PUBLIC_URL", f"http://0.0.0.0:{default_port}")


def get_port() -> int:
    """Get port for agent server."""
    return int(os.getenv("PORT", "8000"))
