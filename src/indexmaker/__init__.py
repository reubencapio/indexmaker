"""
Index Maker - A domain-driven Python module for creating financial indices.

This module provides an intuitive, type-safe API for creating, managing,
and analyzing financial indices. Designed for index professionals.

Example (Traditional API):
    >>> from indexmaker import Index, Universe, WeightingMethod, Currency
    >>>
    >>> index = Index.create(
    ...     name="Tech Leaders Index",
    ...     identifier="TECHLDRS",
    ...     currency=Currency.USD,
    ...     base_date="2025-01-01",
    ...     base_value=1000.0
    ... )
    >>>
    >>> universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL"])
    >>> index.set_universe(universe)
    >>> index.set_weighting_method(WeightingMethod.equal_weight())
    >>>
    >>> value = index.calculate(date="2025-11-15")

Example (AI-Powered):
    >>> from indexmaker.ai import IndexAI
    >>>
    >>> ai = IndexAI()  # Uses OPENAI_API_KEY env var
    >>> result = ai.create_index(
    ...     "Create an equal-weight index of the FAANG stocks"
    ... )
    >>> print(result.index)
    >>> print(result.explanation)
"""

from indexmaker.core.constituent import Constituent
from indexmaker.core.index import Index
from indexmaker.core.types import (
    AssetClass,
    Country,
    Currency,
    Factor,
    IndexType,
    Industry,
    Region,
    Sector,
)
from indexmaker.core.universe import Universe, UniverseBuilder
from indexmaker.data.connectors.base import DataConnector
from indexmaker.data.connectors.yahoo import YahooFinanceConnector
from indexmaker.data.provider import DataProvider, DataProviderBuilder
from indexmaker.rebalancing.schedule import RebalancingSchedule, RebalancingScheduleBuilder
from indexmaker.selection.composite import CompositeScore, CompositeScoreBuilder
from indexmaker.selection.criteria import SelectionCriteria, SelectionCriteriaBuilder
from indexmaker.validation.report import ValidationReport
from indexmaker.validation.rules import ValidationRules, ValidationRulesBuilder
from indexmaker.weighting.methods import WeightingMethod, WeightingMethodBuilder

# Optional AI module (requires openai package)
try:
    from indexmaker.ai import IndexAI, IndexAIConfig
except ImportError:
    IndexAI = None  # type: ignore
    IndexAIConfig = None  # type: ignore

__version__ = "0.1.1"

__all__ = [
    # Core
    "Index",
    "Universe",
    "UniverseBuilder",
    "Constituent",
    # Types
    "Currency",
    "IndexType",
    "AssetClass",
    "Region",
    "Country",
    "Factor",
    "Sector",
    "Industry",
    # Selection
    "SelectionCriteria",
    "SelectionCriteriaBuilder",
    "CompositeScore",
    "CompositeScoreBuilder",
    # Weighting
    "WeightingMethod",
    "WeightingMethodBuilder",
    # Rebalancing
    "RebalancingSchedule",
    "RebalancingScheduleBuilder",
    # Data
    "DataProvider",
    "DataProviderBuilder",
    "DataConnector",
    "YahooFinanceConnector",
    # Validation
    "ValidationRules",
    "ValidationRulesBuilder",
    "ValidationReport",
    # AI (optional)
    "IndexAI",
    "IndexAIConfig",
]
