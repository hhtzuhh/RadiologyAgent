"""Orchestrator Helper Tools.

Functions for managing investigation plans, step status tracking, and synthesis.
"""
import logging
import json
from typing import Optional, List, Dict, Any
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


def display_investigation_plan(tool_context: ToolContext, plan_json: str):
    """
    Displays investigation plan and saves it to session state with status tracking.

    Args:
        tool_context: Tool execution context
        plan_json: JSON array of step objects, each with 'step', 'agent', 'description'

    Returns:
        Dict with plan status
    """
    try:
        plan = json.loads(plan_json)
        enriched_plan = []
        for step_obj in plan:
            enriched_plan.append({
                **step_obj,
                "status": "pending",
                "error": None
            })

        tool_context.state['investigation_plan'] = enriched_plan
        tool_context.state['current_step'] = 1
        tool_context.state['total_steps'] = len(enriched_plan)
        tool_context.state['plan_status'] = 'in_progress'

        logger.info(f"📋 Plan saved to state: {len(enriched_plan)} steps")
        return {
            "status": "plan_displayed",
            "plan": enriched_plan,
            "total_steps": len(enriched_plan)
        }
    except json.JSONDecodeError as e:
        logger.error(f"Could not decode plan_json: {e}")
        return {"status": "error", "message": "Invalid JSON format for plan."}


def update_step_status(
    tool_context: ToolContext,
    step_number: int,
    status: str,
    error_message: Optional[str] = None
):
    """
    Update the status of a specific step in the investigation plan.

    Args:
        tool_context: Tool execution context
        step_number: Step number (1-indexed)
        status: New status ('completed', 'failed')
        error_message: Optional error message if status is 'failed'

    Returns:
        Dict with update status
    """
    plan = tool_context.state.get('investigation_plan')
    if not plan:
        return {"status": "error", "message": "No plan in state"}

    step_index = step_number - 1
    if not (0 <= step_index < len(plan)):
        return {"status": "error", "message": f"Invalid step number: {step_number}"}

    step = plan[step_index]
    old_status = step['status']
    step['status'] = status

    if status == 'failed':
        step['error'] = error_message
        logger.error(f"❌ Step {step_number} ({step['agent']}) failed: {error_message}")
    else:
        logger.info(f"✅ Step {step_number} ({step['agent']}) completed")

    tool_context.state['investigation_plan'] = plan

    if status == 'completed':
        tool_context.state['current_step'] = step_number + 1
        if all(s['status'] == 'completed' for s in plan):
            tool_context.state['plan_status'] = 'completed'
            logger.info("🎉 All steps completed!")

    return {
        "status": "updated",
        "step": step_number,
        "old_status": old_status,
        "new_status": status,
        "plan": plan
    }


def aggregate_findings(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Aggregates all findings from specialized agents into a structured format.

    This tool pulls results from session state saved by Search, Vision, and Knowledge agents
    and organizes them for synthesis into a final answer.

    Args:
        tool_context: Tool execution context with access to session state

    Returns:
        Dictionary containing aggregated findings from all agents
    """
    aggregated = {
        "status": "success",
        "search_results": None,
        "vision_results": None,
        "knowledge_results": None,
        "metadata": {}
    }

    # Aggregate Search Agent results
    if 'search_results' in tool_context.state:
        search_data = tool_context.state['search_results']

        # Handle both list and dict formats
        if isinstance(search_data, list):
            reports = search_data[:10]  # Top 10 for synthesis
            total = len(search_data)
        elif isinstance(search_data, dict):
            # If it's a dict, it might have a 'results' key or be the results themselves
            if 'results' in search_data:
                reports = search_data['results'][:10] if isinstance(search_data['results'], list) else search_data
                total = len(search_data.get('results', []))
            else:
                reports = search_data
                total = 1
        else:
            reports = []
            total = 0

        aggregated["search_results"] = {
            "total_results": total,
            "strategy_used": tool_context.state.get('search_strategy', 'unknown'),
            "search_metadata": tool_context.state.get('search_metadata', {}),
            "reports": reports,
        }
        logger.info(f"📊 Aggregated {total} search results")

    # Aggregate Vision Agent results
    if 'vision_similar_images' in tool_context.state:
        vision_data = tool_context.state['vision_similar_images']
        vision_meta = tool_context.state.get('vision_metadata', {})
        aggregated["vision_results"] = {
            "total_similar_cases": len(vision_data),
            "avg_similarity_score": vision_meta.get('avg_similarity_score', 0),
            "similar_cases": vision_data,
            "source_report_id": vision_meta.get('source_report_id')
        }
        logger.info(f"👁️ Aggregated {len(vision_data)} visually similar cases")

    # Aggregate Knowledge Agent results
    if 'knowledge_analysis' in tool_context.state:
        knowledge_data = tool_context.state['knowledge_analysis']
        aggregated["knowledge_results"] = knowledge_data
        logger.info(f"🧠 Aggregated knowledge analysis results")

    # Add investigation plan metadata
    if 'investigation_plan' in tool_context.state:
        aggregated["metadata"]["investigation_plan"] = tool_context.state['investigation_plan']
        aggregated["metadata"]["completed_steps"] = [
            s for s in tool_context.state['investigation_plan'] if s['status'] == 'completed'
        ]

    logger.info(f"✅ Aggregation complete. Found data from {sum([1 for k,v in aggregated.items() if v and k != 'status' and k != 'metadata'])} agents")

    return aggregated


def format_citations(
    tool_context: ToolContext,
    report_ids: List[str],
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Formats report IDs into readable citations with optional metadata.

    Args:
        tool_context: Tool execution context
        report_ids: List of report IDs to cite
        include_details: Whether to include patient IDs and labels

    Returns:
        Dictionary with formatted citations
    """
    citations = []

    # Get search results from state if available for enrichment
    search_results = tool_context.state.get('search_results', [])
    search_dict = {r.get('report_id'): r for r in search_results} if search_results else {}

    for idx, report_id in enumerate(report_ids, 1):
        citation = {
            "citation_number": idx,
            "report_id": report_id
        }

        if include_details and report_id in search_dict:
            report_data = search_dict[report_id]
            citation["patient_id"] = report_data.get('patient_id')
            citation["findings"] = report_data.get('chexbert_labels', {})

        citations.append(citation)

    # Format as markdown string
    markdown_citations = []
    for c in citations:
        if include_details and 'patient_id' in c:
            markdown_citations.append(
                f"[{c['citation_number']}] Patient {c['patient_id']} - Report: {c['report_id']}"
            )
        else:
            markdown_citations.append(
                f"[{c['citation_number']}] {c['report_id']}"
            )

    return {
        "status": "success",
        "citations": citations,
        "markdown": "\n".join(markdown_citations),
        "total_citations": len(citations)
    }


def generate_synthesis_prompt(tool_context: ToolContext, user_query: str) -> Dict[str, Any]:
    """
    Generates a structured prompt for the orchestrator to synthesize final answer.

    This helper creates a comprehensive synthesis instruction based on aggregated findings,
    helping the orchestrator produce a well-structured, cited response.

    Args:
        tool_context: Tool execution context
        user_query: Original user query

    Returns:
        Dictionary with synthesis prompt and structure
    """
    aggregated = aggregate_findings(tool_context)

    # Build synthesis structure
    synthesis_structure = {
        "user_query": user_query,
        "available_evidence": [],
        "synthesis_guidelines": []
    }

    # Identify what evidence we have
    if aggregated.get("search_results"):
        synthesis_structure["available_evidence"].append(
            f"Search results: {aggregated['search_results']['total_results']} reports found using {aggregated['search_results']['strategy_used']}"
        )
        synthesis_structure["synthesis_guidelines"].append(
            "Include specific findings from the retrieved reports with citations"
        )

    if aggregated.get("vision_results"):
        synthesis_structure["available_evidence"].append(
            f"Vision analysis: {aggregated['vision_results']['total_similar_cases']} visually similar cases (avg similarity: {aggregated['vision_results']['avg_similarity_score']})"
        )
        synthesis_structure["synthesis_guidelines"].append(
            "Mention visual similarity findings and reference similar case patterns"
        )

    if aggregated.get("knowledge_results"):
        synthesis_structure["available_evidence"].append(
            "Knowledge analysis: RadGraph entities and relationships extracted"
        )
        synthesis_structure["synthesis_guidelines"].append(
            "Incorporate medical knowledge relationships from RadGraph analysis"
        )

    # Create synthesis prompt
    prompt = f"""You must now synthesize a final answer to the user's query: "{user_query}"

Available Evidence:
{chr(10).join('- ' + e for e in synthesis_structure['available_evidence'])}

Synthesis Guidelines:
{chr(10).join(f'{i+1}. ' + g for i, g in enumerate(synthesis_structure['synthesis_guidelines']))}

Additional Requirements:
- Start with a direct answer to the user's question
- Support your answer with specific evidence from the aggregated findings
- Include citations using report IDs in [brackets]
- Explain the reasoning that connects the evidence to your conclusion
- If the evidence is insufficient, acknowledge limitations
- Keep the response concise but comprehensive (2-4 paragraphs)

Format your response as:
1. Direct Answer (1-2 sentences)
2. Supporting Evidence (with citations)
3. Medical Reasoning
4. Limitations (if any)
"""

    logger.info(f"📝 Generated synthesis prompt with {len(synthesis_structure['available_evidence'])} evidence sources")

    return {
        "status": "success",
        "synthesis_prompt": prompt,
        "structure": synthesis_structure,
        "aggregated_data": aggregated
    }

