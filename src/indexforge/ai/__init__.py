"""
AI-powered index creation module.

This module provides LLM-powered tools for creating financial indices
from natural language descriptions.

Example:
    >>> from indexforge.ai import IndexAI
    >>>
    >>> ai = IndexAI()  # Uses OPENAI_API_KEY environment variable
    >>> index = ai.create_index(
    ...     "Create a tech-focused index with the top 10 US technology companies, "
    ...     "weighted by market cap with a 15% single stock cap"
    ... )
    >>> print(index)
"""

from indexforge.ai.llm_index_creator import IndexAI, IndexAIConfig

__all__ = [
    "IndexAI",
    "IndexAIConfig",
]
