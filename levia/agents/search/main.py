"""Search Agent A2A Server - Exposes Elasticsearch search via A2A protocol."""
import os
import sys
import logging

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.agent_to_a2a import to_a2a
from shared.config import get_public_url, get_port

# Choose agent implementation:
# Option 1: Dummy agent (no Elasticsearch needed) - for testing A2A
# from agent_dummy import DummySearchAgent as SearchAgent

# Option 2: Real agent with RRF + query refinement (requires Elasticsearch)
from agent_with_refinement import SearchAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Get configuration
PORT = get_port()
PUBLIC_URL = get_public_url(default_port=PORT)

# Create the agent
logger.info("Creating Search Agent...")
search_agent = SearchAgent()

app = to_a2a(search_agent, port=PORT, public_url=PUBLIC_URL)


if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("Starting Search Agent (RRF Hybrid Search + Query Refinement)")
    logger.info("=" * 60)
    logger.info(f"Port: {PORT}")
    logger.info(f"Public URL: {PUBLIC_URL}")
    logger.info("")
    logger.info("Endpoints:")
    logger.info(f"  Agent card: http://0.0.0.0:{PORT}/.well-known/agent.json")
    logger.info("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
