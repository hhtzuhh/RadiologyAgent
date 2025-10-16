"""Search Agent - Entry point for adk web.

This is the main agent file that adk web looks for.
It must export a 'root_agent' variable for ADK discovery.
"""
from .agent_with_refinement import SearchAgent

# ADK web looks for this specific variable name
root_agent = SearchAgent()
