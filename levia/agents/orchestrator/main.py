"""Main entry point for Orchestrator Agent.

Converts the orchestrator agent to A2A Starlette application
and runs it with uvicorn.
"""
import os
import sys
import logging

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.agent_to_a2a import to_a2a
from shared.config import get_public_url, get_port

# Choose orchestration approach:
# Option 1: Simple LLM-driven (like Summoner) - flexible, 130 lines
from agent_simple import create_orchestrator_agent

# Option 2: Programmatic (full control) - predictable, 419 lines
# from agent import OrchestratorAgent as create_orchestrator_agent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_app():
    """Create the Orchestrator A2A application."""
    # Initialize orchestrator agent (LLM-driven, simple!)
    orchestrator = create_orchestrator_agent()

    # Get configuration
    port = get_port()
    public_url = get_public_url(default_port=port)

    logger.info(f"Creating Orchestrator A2A app on port {port}")
    logger.info(f"Public URL: {public_url}")

    # Convert to A2A Starlette app
    app = to_a2a(
        agent=orchestrator,
        port=port,
        public_url=public_url
    )

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = get_port()

    logger.info("=" * 60)
    logger.info("Starting Orchestrator Agent (LLM-Driven)")
    logger.info("=" * 60)
    logger.info(f"Orchestrator running on port: {port}")
    logger.info(f"Orchestrator public URL: {get_public_url(default_port=port)}")
    logger.info("")
    logger.info("Agent Discovery (from environment variables):")
    logger.info(f"  SEARCH_AGENT_URL:    {os.getenv('SEARCH_AGENT_URL', 'NOT SET')}")
    logger.info(f"  VISION_AGENT_URL:    {os.getenv('VISION_AGENT_URL', 'NOT SET')}")
    logger.info(f"  KNOWLEDGE_AGENT_URL: {os.getenv('KNOWLEDGE_AGENT_URL', 'NOT SET')}")
    logger.info(f"  SYNTHESIS_AGENT_URL: {os.getenv('SYNTHESIS_AGENT_URL', 'NOT SET')}")

    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
