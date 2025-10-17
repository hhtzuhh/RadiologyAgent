"""Search Agent A2A Server - Exposes Elasticsearch search via A2A protocol."""
import os
import sys
import logging

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.agent_to_a2a import to_a2a
from shared.config import get_public_url, get_port

from .agent import SearchAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_app():
    """Create the Search A2A application."""
    # Create the agent
    logger.info("Creating Search Agent...")
    search_agent = SearchAgent()

    # Get configuration
    port = get_port()
    public_url = get_public_url(default_port=port)

    logger.info(f"Creating Search A2A app on port {port}")
    logger.info(f"Public URL: {public_url}")

    # Convert to A2A Starlette app
    app = to_a2a(
        agent=search_agent,
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
    logger.info("Starting Search Agent")
    logger.info("=" * 60)
    logger.info(f"Port: {port}")
    logger.info(f"Public URL: {get_public_url(default_port=port)}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="info"
    )
