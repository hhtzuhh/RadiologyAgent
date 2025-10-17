"""Orchestrator Agent - Multi-Agent Radiology Intelligence System.

This orchestrator coordinates specialized agents to investigate complex clinical questions
through autonomous collaboration, using Google A2A (Agent-to-Agent) communication style.

Agent Architecture:
- Orchestrator: Query understanding, task decomposition, coordination
- Search Agent: Information retrieval with adaptive search strategies
- Vision Agent: Medical image analysis and feature extraction
- Knowledge Agent: Medical knowledge reasoning and validation
- Synthesis Agent: Final answer generation with citations
"""
import os
import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH


logger = logging.getLogger(__name__)


def create_orchestrator_agent():
    """
    Create an LLM-driven orchestrator agent for multi-agent radiology intelligence.

    The orchestrator autonomously:
    - Validates and refines user queries
    - Decomposes complex clinical questions into subtasks
    - Coordinates specialized agents in optimal execution order
    - Evaluates intermediate results and triggers self-correction
    - Maintains conversation state for follow-up questions

    Returns:
        LlmAgent: Configured orchestrator with all sub-agent connections
    """
    # Get agent URLs from environment
    search_url = os.getenv("SEARCH_AGENT_URL")
    vision_url = os.getenv("VISION_AGENT_URL")
    knowledge_url = os.getenv("KNOWLEDGE_AGENT_URL")
    synthesis_url = os.getenv("SYNTHESIS_AGENT_URL")

    logger.info("=" * 80)
    logger.info("Initializing Multi-Agent Radiology Intelligence Orchestrator")
    logger.info("=" * 80)
    logger.info(f"  [Search]     {search_url or 'Not configured'}")
    logger.info(f"  [Vision]     {vision_url or 'Not configured'}")
    logger.info(f"  [Knowledge]  {knowledge_url or 'Not configured'}")
    logger.info(f"  [Synthesis]  {synthesis_url or 'Not configured'}")
    logger.info("=" * 80)

    # Create remote agent connections using A2A protocol
    sub_agents = []

    if search_url:
        sub_agents.append(RemoteA2aAgent(
            name="search_agent",
            description=(
                "Elasticsearch search agent with adaptive strategy selection. "
                "Capabilities: "
                "- BM25 keyword search for precise medical terms "
                "- kNN semantic search for conceptual queries "
                "- Hybrid search combining both strategies "
                "- Multimodal search using image embeddings "
                "- Label filtering (CheXbert 14 disease labels) "
                "- Patient ID and temporal filtering "
                "- Result quality evaluation and strategy adaptation "
                "Use for: finding relevant radiology cases, co-occurrence analysis, "
                "comparative searches, similar case retrieval."
            ),
            agent_card=f"{search_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))
        logger.info("  + Search Agent registered")

    if vision_url:
        sub_agents.append(RemoteA2aAgent(
            name="vision_agent",
            description=(
                "Vision analysis agent using Gemini Vision API. "
                "Capabilities: "
                "- Anatomical structure identification "
                "- Abnormality detection and description "
                "- Visual feature extraction for search queries "
                "- Image embedding generation for similarity search "
                "- Medical image interpretation and annotation "
                "Use for: analyzing uploaded X-rays, extracting visual features "
                "for search filters, generating image embeddings, visual question answering."
            ),
            agent_card=f"{vision_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))
        logger.info("  + Vision Agent registered")

    if knowledge_url:
        sub_agents.append(RemoteA2aAgent(
            name="knowledge_agent",
            description=(
                "Knowledge graph and RadGraph analysis agent. "
                "Capabilities: "
                "- RadGraph entity extraction (anatomical, observation, disease) "
                "- Relationship triplet parsing (entity -> relation -> entity) "
                "- Medical term validation and ontology mapping "
                "- Pattern detection across multiple cases "
                "- Correlation and causation analysis "
                "- CheXbert label verification "
                "Use for: validating search results, extracting relationships, "
                "identifying causal mechanisms, cross-agent validation."
            ),
            agent_card=f"{knowledge_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))
        logger.info("  + Knowledge Agent registered")

    if synthesis_url:
        sub_agents.append(RemoteA2aAgent(
            name="synthesis_agent",
            description=(
                "Synthesis agent for generating comprehensive, citation-backed answers. "
                "Capabilities: "
                "- Evidence aggregation from multiple agents "
                "- Medical report synthesis with clinical language "
                "- Citation generation (patient IDs, report references) "
                "- Explanation generation with reasoning traces "
                "- Draft report section generation (Findings, Impression) "
                "- Multi-source corroboration and summarization "
                "Use for: generating final answers, creating comprehensive responses, "
                "synthesizing evidence, producing explainable outputs."
            ),
            agent_card=f"{synthesis_url}/{AGENT_CARD_WELL_KNOWN_PATH}"
        ))
        logger.info("  + Synthesis Agent registered")

    # Create the LLM-driven orchestrator with comprehensive instructions
    orchestrator = LlmAgent(
        name="orchestrator",
        model="gemini-2.0-flash",
        instruction="""You are the Orchestrator Agent for a Multi-Agent Radiology Intelligence System.

Your role is to coordinate specialized agents to investigate complex clinical questions through
autonomous collaboration. You must maintain clear intelligence domain boundaries and enable
each agent to work within its expertise.

===============================================================================
INTELLIGENCE DOMAIN BOUNDARIES (CRITICAL)
===============================================================================

You (Orchestrator):
+ Query validation and refinement
+ Task decomposition into subtasks
+ Agent coordination and sequencing
+ Quality evaluation of intermediate results
+ Conversation state management
- DO NOT choose search strategies (search_agent's job)
- DO NOT interpret medical findings (synthesis_agent's job)

search_agent:
+ Search strategy selection (BM25, kNN, hybrid, multimodal)
+ Result quality evaluation and adaptation
+ Filter application (labels, patient IDs, dates)
- DO NOT reject vague queries (orchestrator's job)
- DO NOT interpret medical meaning (synthesis_agent's job)

vision_agent:
+ Image analysis and feature extraction
+ Anatomical structure identification
+ Visual abnormality detection
- DO NOT validate against RadGraph (knowledge_agent's job)

knowledge_agent:
+ RadGraph traversal and entity extraction
+ Medical term validation
+ Relationship pattern detection
- DO NOT generate final explanations (synthesis_agent's job)

synthesis_agent:
+ Medical reasoning and interpretation
+ Evidence aggregation and explanation
+ Citation-backed answer generation
- DO NOT perform searches (search_agent's job)

===============================================================================
STANDARD INVESTIGATION WORKFLOW
===============================================================================

1. QUERY ANALYSIS & VALIDATION
   - Classify query type: factual retrieval, correlation, causation, similarity, VQA
   - Check if query is specific enough (if not, ask clarifying questions)
   - Determine required agents based on query type

2. TASK DECOMPOSITION
   Examples:
   - "Why do patients with X often have Y?" ->
     Task 1: Find co-occurrence frequency (search_agent)
     Task 2: Extract relationships (knowledge_agent)
     Task 3: Find explanatory text (search_agent with refined query)
     Task 4: Synthesize causal explanation (synthesis_agent)

   - "What is in this X-ray?" ->
     Task 1: Analyze image (vision_agent)
     Task 2: Find similar cases (search_agent with image embedding)
     Task 3: Synthesize findings (synthesis_agent)

   - "Find cases with condition X" ->
     Task 1: Search with appropriate strategy (search_agent)
     Task 2: Generate summary (synthesis_agent)

3. PARALLEL EXECUTION (when applicable)
   - vision_agent and initial search_agent queries can run concurrently
   - Knowledge validation can happen in parallel with result aggregation

4. QUALITY EVALUATION & SELF-CORRECTION
   After each subtask, evaluate:
   - Are results sufficient? (check result count, relevance scores)
   - If search_agent returns weak results: it should retry with different strategy
   - If knowledge_agent finds inconsistencies: refine search parameters
   - Maximum 2-3 retry attempts per subtask

5. SYNTHESIS & RESPONSE
   - Aggregate all agent outputs
   - Call synthesis_agent to generate final answer
   - Include reasoning traces showing each agent's contribution
   - Provide citations (patient IDs, report references)

===============================================================================
QUERY TYPE HANDLING
===============================================================================

A. Evidence Retrieval & Corroboration (Text Input)
   Examples:
   - "What is the latest report for patient TCGA-123 regarding cardiac issues?"
   - "Find reports with Pleural Effusion that mention size"
   -> Use search_agent with appropriate filters

B. Visual Correlation & Similarity (Image Input)
   Examples:
   - [Image] "Find similar cases with confirmed Lung Lesion"
   - [Image] "What is the positional reasoning for the Support Device?"
   -> Use vision_agent first, then search_agent with image embedding

C. Correlation & Causation Questions
   Examples:
   - "Why do patients with X often have Y?"
   - "What is the relationship between X and Y?"
   -> Multi-step: search_agent -> knowledge_agent -> refined search -> synthesis_agent

D. Workflow & Reporting Assistance
   Examples:
   - "Generate a draft impression for these findings"
   - "Is it standard to classify X as Y?"
   -> Use search_agent for precedent cases, synthesis_agent for generation

===============================================================================
IMPORTANT RULES
===============================================================================

1. Always start with search_agent for evidence gathering (unless image analysis is needed first)
2. Each agent logs its decisions - maintain audit trail
3. Agent outputs include metadata (scores, strategies used, result counts)
4. If any agent fails or returns insufficient results, evaluate and adapt
5. For follow-up questions, reference previous agent outputs (conversation memory)
6. Provide explainable reasoning by showing each agent's contribution
7. All final answers must be grounded in the CheXpert dataset with citations

===============================================================================
EXAMPLE REASONING TRACE FORMAT
===============================================================================

Final Response should include:
- **Query Analysis:** [Your classification and plan]
- **Agent Coordination:**
  - [Agent Name]: [What it did and why]
  - [Result summary with metadata]
- **Findings:** [Aggregated evidence]
- **Answer:** [Comprehensive response with citations]

Begin investigating!""",
        sub_agents=sub_agents,
    )

    agent_count = len(sub_agents)
    logger.info("=" * 80)
    logger.info(f"Orchestrator initialized with {agent_count} sub-agent(s)")
    logger.info("  Ready for multi-agent collaboration")
    logger.info("=" * 80)

    return orchestrator


# ADK web looks for this specific variable name
root_agent = create_orchestrator_agent()
