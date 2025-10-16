"""Dummy Search Agent - Simple hello world for testing A2A communication.

No Elasticsearch needed! Just uses LlmAgent with a simple instruction.
"""
import logging
from google.adk.agents.llm_agent import LlmAgent


logger = logging.getLogger(__name__)


def DummySearchAgent():
    """
    Create a dummy search agent using LlmAgent for testing A2A communication.

    No Elasticsearch, no complex logic - just a simple LLM that says hello!
    Perfect for testing orchestrator → search agent communication.
    """
    logger.info("Creating Dummy Search Agent (LlmAgent-based, no Elasticsearch needed!)")

    return LlmAgent(
        name="search",
        model="gemini-2.0-flash",
        instruction="""You are a dummy search agent for testing A2A communication.

When you receive any request, respond with a friendly greeting that includes:
1. A wave emoji 👋
2. Acknowledge what the user asked for
3. Explain that you're a test agent and in production you would search Elasticsearch

Keep your response concise and friendly.""",
        description="Dummy search agent for testing. Just says hello!"
    )
