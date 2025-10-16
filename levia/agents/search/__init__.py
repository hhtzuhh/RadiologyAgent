"""Search Agent - Elasticsearch hybrid search with A2A.

Modes:
- DummySearchAgent: No ES needed, just says hello (for testing)
- SearchAgent: RRF hybrid search with query refinement (production)
"""
from .agent_with_refinement import SearchAgent
from .agent_dummy import DummySearchAgent

__all__ = ["SearchAgent", "DummySearchAgent"]
