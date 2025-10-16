"""Convert ADK agents to A2A Starlette applications.

Adapted from agentverse-architect for radiology multi-agent system.
"""
from __future__ import annotations

import logging
import os

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from starlette.applications import Starlette

from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.cli.utils.logs import setup_adk_logger
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder


def to_a2a(
    agent: BaseAgent,
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    public_url: str | None = None
) -> Starlette:
    """
    Convert an ADK agent to an A2A Starlette application.

    This enables the agent to communicate using the A2A protocol,
    making it discoverable and interoperable with other A2A agents.

    Args:
        agent: The ADK agent to convert
        host: The host for the A2A RPC URL (default: "0.0.0.0")
        port: The port for the A2A RPC URL (default: 8000)
        public_url: Public URL for agent card (for cloud deployment)

    Returns:
        A Starlette application that can be run with uvicorn

    Example:
        search_agent = SearchAgent()
        app = to_a2a(search_agent, port=8000, public_url="https://search-agent.run.app")
        # Then run with: uvicorn module:app --host 0.0.0.0 --port 8000
    """
    # Set up ADK logging
    setup_adk_logger(logging.INFO)

    async def create_runner() -> Runner:
        """Create a runner for the agent."""
        return Runner(
            app_name=agent.name or "radiology_agent",
            agent=agent,
            # Use in-memory services for simplicity
            # In production, these could be replaced with persistent services
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
            credential_service=InMemoryCredentialService(),
        )

    # Create A2A components
    task_store = InMemoryTaskStore()

    agent_executor = A2aAgentExecutor(
        runner=create_runner,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store
    )

    # Build agent card for discovery
    # If public_url not provided, use local URL
    if public_url is None:
        public_url = f"http://{host}:{port}/"

    card_builder = AgentCardBuilder(
        agent=agent,
        rpc_url=public_url,
    )

    # Create Starlette app
    app = Starlette()

    # Add startup handler to build agent card and configure A2A routes
    async def setup_a2a():
        """Setup A2A routes during startup."""
        logger = logging.getLogger(__name__)
        logger.info("Building agent card...")

        # Build the agent card asynchronously
        agent_card = await card_builder.build()
        logger.info(f"Agent card built: {agent_card.name}")

        # Create the A2A Starlette application
        a2a_app = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )
        logger.info("A2A application created")

        # Add A2A routes to the main app
        # This exposes:
        # - /.well-known/agent-card (for discovery)
        # - /a2a/v1/tasks (for task submission)
        # - /a2a/v1/tasks/{task_id} (for task status)
        a2a_app.add_routes_to_app(app)
        logger.info("A2A routes added to app")
        logger.info(f"Available routes: {[route.path for route in app.routes]}")

    # Register startup event
    app.add_event_handler("startup", setup_a2a)

    return app