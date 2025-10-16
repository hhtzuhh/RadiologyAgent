"""Simplified Orchestrator Agent - LLM-driven orchestration.

This is the "Summoner style" - let the LLM decide everything!
Much simpler than the programmatic approach.
"""
import os
import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH


logger = logging.getLogger(__name__)


def create_orchestrator_agent():
    """
    Create an LLM-driven orchestrator agent (Summoner style).

    The LLM automatically:
    - Analyzes user queries
    - Decides which agents to call
    - Plans task execution
    - Aggregates results

    Much simpler than programmatic orchestration!
    """
    # Get agent URLs from environment
    search_url = os.getenv("SEARCH_AGENT_URL")
    vision_url = os.getenv("VISION_AGENT_URL")
    knowledge_url = os.getenv("KNOWLEDGE_AGENT_URL")
    synthesis_url = os.getenv("SYNTHESIS_AGENT_URL")

    logger.info(f"Initializing LLM-driven orchestrator")
    logger.info(f"  Search: {search_url}")
    logger.info(f"  Vision: {vision_url}")
    logger.info(f"  Knowledge: {knowledge_url}")
    logger.info(f"  Synthesis: {synthesis_url}")

    # Create remote agent connections
    sub_agents = []

    if search_url:
        sub_agents.append(RemoteA2aAgent(
            name="search_agent",
            description=(
                "Elasticsearch search agent for radiology reports. "
                "Use for: finding cases, hybrid search (text+image), "
                "co-occurrence analysis, filtering by patient IDs."
            ),
            agent_card=f"{search_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))

    if vision_url:
        sub_agents.append(RemoteA2aAgent(
            name="vision_agent",
            description=(
                "Vision analysis agent using Gemini Vision API. "
                "Use for: analyzing medical images, extracting findings, "
                "generating image embeddings for similarity search."
            ),
            agent_card=f"{vision_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))

    if knowledge_url:
        sub_agents.append(RemoteA2aAgent(
            name="knowledge_agent",
            description=(
                "Knowledge graph and RadGraph analysis agent. "
                "Use for: extracting relationships, analyzing correlations, "
                "finding causal mechanisms, pattern detection."
            ),
            agent_card=f"{knowledge_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))

    if synthesis_url:
        sub_agents.append(RemoteA2aAgent(
            name="synthesis_agent",
            description=(
                "Synthesis agent for generating final answers. "
                "Use for: aggregating evidence, writing comprehensive "
                "explanations with citations, generating summaries."
            ),
            agent_card=f"{synthesis_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))

    # Create the LLM-driven orchestrator
    orchestrator = LlmAgent(
        name="orchestrator",
        model="gemini-2.0-flash",
        instruction="""You are a Radiology Intelligence Orchestrator coordinating specialized agents.

Analyze user queries and coordinate agents to provide comprehensive answers.

PROCESS:
1. Analyze the query type
2. Call search_agent to find relevant cases
3. Use knowledge_agent to extract relationships if needed
4. Use synthesis_agent to generate final answer with citations

AGENTS:
- search_agent: Find radiology cases
- vision_agent: Analyze medical images
- knowledge_agent: Extract relationships and correlations
- synthesis_agent: Generate comprehensive answers

Always start with search_agent for evidence gathering.""",
        sub_agents=sub_agents,
    )

    logger.info(f"Orchestrator initialized with {len(sub_agents)} sub-agents")

    return orchestrator


# Export the orchestrator
OrchestratorAgent = create_orchestrator_agent
