"""Orchestrator Agent - Query analysis and multi-agent coordination using Google ADK.

This agent uses RemoteA2aAgent to communicate directly with other agents
following the True Direct A2A architecture (no message broker).
"""
import os
import logging
from typing import Dict, Any, List
from enum import Enum

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.agents.context import GenerateContext
from google.adk.artifacts.artifact import Artifact
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of radiology queries."""
    SIMPLE_SEARCH = "simple_search"          # "Find pneumothorax cases"
    CORRELATION = "correlation"              # "Why do X and Y occur together?"
    EXPLANATION = "explanation"              # "What causes X?"
    DIFFERENTIAL = "differential"            # "What could cause these findings?"
    IMAGE_SEARCH = "image_search"            # Search by image similarity


class AgentTask(BaseModel):
    """Task to be executed by an agent."""
    agent: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - Central coordinator for radiology investigations.

    Responsibilities:
    1. Analyze user query and classify query type
    2. Decompose complex queries into agent tasks
    3. Coordinate task execution (sequential or parallel)
    4. Aggregate results from multiple agents
    5. Generate final response

    Uses Google ADK RemoteA2aAgent for direct HTTP communication
    with other agents (no message broker).
    """

    def __init__(self):
        super().__init__(
            name="orchestrator",
            description="Orchestrator agent that analyzes queries and coordinates "
                       "multiple specialized agents (search, vision, knowledge, synthesis) "
                       "for comprehensive radiology investigations.",
        )

        # Initialize remote agent connections (Direct A2A!)
        self.search_url = os.getenv("SEARCH_AGENT_URL")
        self.vision_url = os.getenv("VISION_AGENT_URL")
        self.knowledge_url = os.getenv("KNOWLEDGE_AGENT_URL")
        self.synthesis_url = os.getenv("SYNTHESIS_AGENT_URL")

        logger.info(f"Orchestrator initialized with agent URLs:")
        logger.info(f"  Search: {self.search_url}")
        logger.info(f"  Vision: {self.vision_url}")
        logger.info(f"  Knowledge: {self.knowledge_url}")
        logger.info(f"  Synthesis: {self.synthesis_url}")

        # Initialize remote agents for direct A2A communication
        self.agents: Dict[str, RemoteA2aAgent] = {}
        self._init_remote_agents()

    def _init_remote_agents(self):
        """Initialize RemoteA2aAgent connections to other agents."""
        agent_urls = {
            "search": self.search_url,
            "vision": self.vision_url,
            "knowledge": self.knowledge_url,
            "synthesis": self.synthesis_url,
        }

        for agent_name, url in agent_urls.items():
            if url:
                try:
                    self.agents[agent_name] = RemoteA2aAgent(
                        agent_card_url=f"{url}/.well-known/agent-card"
                    )
                    logger.info(f"Connected to {agent_name} agent at {url}")
                except Exception as e:
                    logger.error(f"Failed to connect to {agent_name} agent: {e}")
            else:
                logger.warning(f"No URL configured for {agent_name} agent")

    async def generate(self, context: GenerateContext) -> Artifact:
        """
        Main entry point for orchestration.

        Flow:
        1. Analyze query → determine query type
        2. Plan tasks → create task graph
        3. Execute tasks → coordinate agents
        4. Aggregate results → compile evidence
        5. Generate response → synthesize answer

        Args:
            context: ADK GenerateContext containing user query

        Returns:
            Artifact containing final response with citations
        """
        user_query = context.user_content.text
        logger.info(f"Orchestrator received query: {user_query[:100]}")

        try:
            # Step 1: Analyze query
            analysis = await self._analyze_query(user_query, context)
            logger.info(f"Query type: {analysis['query_type']}")

            # Step 2: Plan tasks
            tasks = self._plan_tasks(analysis)
            logger.info(f"Planned {len(tasks)} tasks")

            # Step 3: Execute tasks
            results = await self._execute_tasks(tasks, context)
            logger.info(f"Executed {len(results)} tasks")

            # Step 4: Aggregate results
            aggregated = self._aggregate_results(results)

            # Step 5: Generate final response (via Synthesis agent)
            final_response = await self._generate_response(
                query=user_query,
                analysis=analysis,
                results=aggregated,
                context=context
            )

            return Artifact(content=final_response)

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            return Artifact(content=f"Error: {str(e)}")

    async def _analyze_query(self, query: str, context: GenerateContext) -> Dict[str, Any]:
        """
        Analyze query to determine type and extract key information.

        Uses simple keyword matching. In production, use LLM for classification.
        """
        query_lower = query.lower()

        # Determine query type
        if any(word in query_lower for word in ["why", "correlation", "relationship", "together"]):
            query_type = QueryType.CORRELATION
        elif any(word in query_lower for word in ["what causes", "explain", "mechanism"]):
            query_type = QueryType.EXPLANATION
        elif any(word in query_lower for word in ["differential", "could be", "possibilities"]):
            query_type = QueryType.DIFFERENTIAL
        elif context.session_metadata.get("image_provided"):
            query_type = QueryType.IMAGE_SEARCH
        else:
            query_type = QueryType.SIMPLE_SEARCH

        # Extract entities (conditions, anatomies, etc.)
        # In production, use NER or LLM extraction
        entities = self._extract_entities(query)

        return {
            "query_type": query_type,
            "query": query,
            "entities": entities,
            "requires_knowledge_graph": query_type in [QueryType.CORRELATION, QueryType.EXPLANATION],
            "requires_vision": context.session_metadata.get("image_provided", False),
        }

    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract medical entities from query.

        In production, use medical NER model.
        """
        # Simple keyword extraction for demo
        conditions = []
        anatomies = []

        query_lower = query.lower()

        # Common radiology findings
        finding_keywords = [
            "pneumothorax", "pleural effusion", "cardiomegaly", "pneumonia",
            "atelectasis", "consolidation", "edema", "mass", "nodule"
        ]

        anatomy_keywords = [
            "lung", "heart", "pleura", "chest", "thorax", "cardiac", "pulmonary"
        ]

        for keyword in finding_keywords:
            if keyword in query_lower:
                conditions.append(keyword.replace(" ", "_").title())

        for keyword in anatomy_keywords:
            if keyword in query_lower:
                anatomies.append(keyword.title())

        return {
            "conditions": conditions,
            "anatomies": anatomies,
        }

    def _plan_tasks(self, analysis: Dict[str, Any]) -> List[AgentTask]:
        """
        Create task execution plan based on query analysis.

        Returns list of tasks with dependencies for proper sequencing.
        """
        query_type = analysis["query_type"]
        tasks = []

        if query_type == QueryType.SIMPLE_SEARCH:
            # Simple: just search
            tasks.append(AgentTask(
                agent="search",
                action="hybrid_search",
                params={"text_query": analysis["query"]}
            ))

        elif query_type == QueryType.CORRELATION:
            # Complex: search → knowledge → search (for details) → synthesis
            tasks.extend([
                AgentTask(
                    agent="search",
                    action="filter_co_occurrence",
                    params={"analysis": analysis},
                    depends_on=[]
                ),
                AgentTask(
                    agent="knowledge",
                    action="analyze_correlation",
                    params={"analysis": analysis},
                    depends_on=["search"]
                ),
                AgentTask(
                    agent="synthesis",
                    action="generate_explanation",
                    params={"analysis": analysis},
                    depends_on=["knowledge"]
                )
            ])

        elif query_type == QueryType.EXPLANATION:
            # Search → Knowledge (extract causal relationships) → Synthesis
            tasks.extend([
                AgentTask(
                    agent="search",
                    action="hybrid_search",
                    params={"text_query": analysis["query"]},
                    depends_on=[]
                ),
                AgentTask(
                    agent="knowledge",
                    action="extract_mechanisms",
                    params={"analysis": analysis},
                    depends_on=["search"]
                ),
                AgentTask(
                    agent="synthesis",
                    action="generate_explanation",
                    params={"analysis": analysis},
                    depends_on=["knowledge"]
                )
            ])

        elif query_type == QueryType.IMAGE_SEARCH:
            # Vision → Search (using embeddings) → Synthesis
            tasks.extend([
                AgentTask(
                    agent="vision",
                    action="analyze_image",
                    params={"image_data": analysis.get("image_data")},
                    depends_on=[]
                ),
                AgentTask(
                    agent="search",
                    action="hybrid_search",
                    params={"use_vision_results": True},
                    depends_on=["vision"]
                ),
                AgentTask(
                    agent="synthesis",
                    action="generate_summary",
                    params={"analysis": analysis},
                    depends_on=["search"]
                )
            ])

        else:
            # Default: just search
            tasks.append(AgentTask(
                agent="search",
                action="hybrid_search",
                params={"text_query": analysis["query"]}
            ))

        return tasks

    async def _execute_tasks(
        self,
        tasks: List[AgentTask],
        context: GenerateContext
    ) -> Dict[str, Any]:
        """
        Execute tasks in proper order based on dependencies.

        Uses RemoteA2aAgent for direct HTTP communication.
        """
        results = {}
        executed = set()

        # Simple dependency resolution (topological sort would be better)
        max_iterations = len(tasks) + 1
        iteration = 0

        while len(executed) < len(tasks) and iteration < max_iterations:
            iteration += 1

            for task in tasks:
                # Skip if already executed
                if task.agent in executed:
                    continue

                # Check if dependencies are satisfied
                deps_satisfied = all(dep in executed for dep in task.depends_on)

                if deps_satisfied:
                    logger.info(f"Executing task: {task.agent}.{task.action}")

                    # DIRECT A2A COMMUNICATION HERE!
                    result = await self._call_agent(
                        agent_name=task.agent,
                        action=task.action,
                        params=task.params,
                        previous_results=results,
                        context=context
                    )

                    results[task.agent] = result
                    executed.add(task.agent)

        return results

    async def _call_agent(
        self,
        agent_name: str,
        action: str,
        params: Dict,
        previous_results: Dict,
        context: GenerateContext
    ) -> Dict[str, Any]:
        """
        Call another agent directly via A2A protocol.

        This is TRUE Direct A2A - HTTP call to agent's endpoint!
        """
        if agent_name not in self.agents:
            logger.error(f"Agent {agent_name} not available")
            return {"error": f"Agent {agent_name} not configured"}

        try:
            # Direct A2A call via RemoteA2aAgent
            remote_agent = self.agents[agent_name]

            logger.info(f"[Orchestrator] Calling {agent_name} agent directly...")
            logger.info(f"  Action: {action}, Params: {params}")

            # Execute remote agent task
            # Note: In ADK, the context is passed directly to the agent
            # The agent will parse the context to extract action/params
            response = await remote_agent.generate(context)

            logger.info(f"[Orchestrator] Received response from {agent_name}")

            # Parse response
            return self._parse_agent_response(response)

        except Exception as e:
            logger.error(f"Failed to call {agent_name} agent: {e}")
            return {"error": str(e)}

    def _parse_agent_response(self, response: Artifact) -> Dict[str, Any]:
        """Parse agent response artifact into dict."""
        try:
            # In production, use structured response format
            import json
            return json.loads(response.content) if isinstance(response.content, str) else {"data": response.content}
        except Exception:
            return {"data": str(response.content)}

    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents.

        Combines evidence, extracts key findings, calculates confidence.
        """
        aggregated = {
            "evidence": [],
            "num_cases": 0,
            "confidence": 0.0,
            "agents_involved": list(results.keys()),
        }

        # Extract search results
        if "search" in results:
            search_data = results["search"].get("results", [])
            aggregated["evidence"].extend(search_data)
            aggregated["num_cases"] = len(search_data)

        # Extract knowledge insights
        if "knowledge" in results:
            aggregated["knowledge_insights"] = results["knowledge"]

        # Extract vision analysis
        if "vision" in results:
            aggregated["vision_analysis"] = results["vision"]

        # Calculate overall confidence
        confidences = []
        for agent_result in results.values():
            if "confidence" in agent_result:
                confidences.append(agent_result["confidence"])

        if confidences:
            aggregated["confidence"] = sum(confidences) / len(confidences)

        return aggregated

    async def _generate_response(
        self,
        query: str,
        analysis: Dict,
        results: Dict,
        context: GenerateContext
    ) -> str:
        """
        Generate final response using Synthesis agent.

        If Synthesis agent not available, generate simple response.
        """
        if "synthesis" in self.agents:
            try:
                # Call Synthesis agent for final answer
                response = await self._call_agent(
                    agent_name="synthesis",
                    action="generate_final_answer",
                    params={
                        "query": query,
                        "analysis": analysis,
                        "results": results
                    },
                    previous_results={},
                    context=context
                )

                return response.get("answer", "No response generated")

            except Exception as e:
                logger.error(f"Synthesis failed: {e}")
                return self._generate_fallback_response(query, results)
        else:
            return self._generate_fallback_response(query, results)

    def _generate_fallback_response(self, query: str, results: Dict) -> str:
        """Generate simple response when Synthesis agent unavailable."""
        num_cases = results.get("num_cases", 0)
        confidence = results.get("confidence", 0.0)

        response = f"Query: {query}\n\n"
        response += f"Found {num_cases} relevant cases.\n"
        response += f"Confidence: {confidence:.2f}\n\n"

        if results.get("evidence"):
            response += "Top findings:\n"
            for i, evidence in enumerate(results["evidence"][:3], 1):
                response += f"{i}. Patient {evidence.get('patient_id', 'N/A')}\n"

        return response
