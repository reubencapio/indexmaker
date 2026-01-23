"""
Composite scoring for multi-factor constituent selection.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from indexforge.core.constituent import Constituent
from indexforge.core.types import Factor


@dataclass
class FactorWeight:
    """A factor and its weight in a composite score."""

    factor: Factor
    weight: float
    ascending: bool = False  # Higher is better by default

    def __post_init__(self):
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Factor weight must be between 0 and 1, got {self.weight}")


@dataclass
class CompositeScore:
    """
    Multi-factor composite score for constituent ranking.

    Combines multiple factors with specified weights to create
    a single score for ranking constituents.

    Attributes:
        factors: List of (Factor, weight) tuples
        normalize: Whether to normalize factor values

    Example:
        >>> score = (CompositeScore.builder()
        ...     .add_factor(Factor.VALUE, weight=0.4)
        ...     .add_factor(Factor.MOMENTUM, weight=0.3)
        ...     .add_factor(Factor.QUALITY, weight=0.3)
        ...     .build()
        ... )
    """

    factor_weights: list[FactorWeight] = field(default_factory=list)
    normalize: bool = True
    custom_factors: dict[str, Callable[[Constituent], float]] = field(default_factory=dict)
    custom_factor_weights: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def builder() -> "CompositeScoreBuilder":
        """Create a new CompositeScoreBuilder."""
        return CompositeScoreBuilder()

    def calculate(self, constituent: Constituent) -> float:
        """
        Calculate composite score for a constituent.

        Args:
            constituent: The constituent to score

        Returns:
            Composite score value
        """
        total_score = 0.0
        total_weight = 0.0

        for fw in self.factor_weights:
            value = self._get_factor_value(constituent, fw.factor)
            if value is not None:
                total_score += value * fw.weight
                total_weight += fw.weight

        # Add custom factors
        for name, factor_fn in self.custom_factors.items():
            weight = self.custom_factor_weights.get(name, 0.0)
            try:
                value = factor_fn(constituent)
                total_score += value * weight
                total_weight += weight
            except Exception:
                pass  # Skip if custom factor fails

        if total_weight > 0:
            return total_score / total_weight
        return 0.0

    def _get_factor_value(self, constituent: Constituent, factor: Factor) -> Optional[float]:
        """Get the value of a factor for a constituent."""
        factor_mapping = {
            Factor.MARKET_CAP: constituent.market_cap,
            Factor.FREE_FLOAT_MARKET_CAP: constituent.free_float_market_cap,
            Factor.LIQUIDITY: constituent.average_daily_volume,
            Factor.VOLUME: constituent.average_daily_volume,
            Factor.DIVIDEND_YIELD: constituent.dividend_yield,
            Factor.PRICE_TO_EARNINGS: constituent.pe_ratio,
            Factor.PRICE_TO_BOOK: constituent.pb_ratio,
            Factor.ROE: getattr(constituent, "roe", None),
            Factor.ROA: getattr(constituent, "roa", None),
        }

        return factor_mapping.get(factor)

    def rank(self, constituents: list[Constituent]) -> list[tuple[Constituent, float]]:
        """
        Rank constituents by composite score.

        Args:
            constituents: List of constituents to rank

        Returns:
            List of (constituent, score) tuples, sorted by score descending
        """
        scored = [(c, self.calculate(c)) for c in constituents]
        return sorted(scored, key=lambda x: x[1], reverse=True)


class CompositeScoreBuilder:
    """
    Builder for constructing CompositeScore with fluent syntax.

    Example:
        >>> score = (CompositeScore.builder()
        ...     .add_factor(Factor.VALUE, weight=0.4)
        ...     .add_factor(Factor.MOMENTUM, weight=0.3)
        ...     .add_factor(Factor.QUALITY, weight=0.3)
        ...     .normalize(True)
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        self._factor_weights: list[FactorWeight] = []
        self._normalize: bool = True
        self._custom_factors: dict[str, Callable[[Constituent], float]] = {}
        self._custom_factor_weights: dict[str, float] = {}

    def add_factor(
        self, factor: Factor, weight: float, ascending: bool = False
    ) -> "CompositeScoreBuilder":
        """
        Add a factor with its weight.

        Args:
            factor: The factor to add
            weight: Weight of the factor (0.0 to 1.0)
            ascending: If True, lower values are better
        """
        self._factor_weights.append(FactorWeight(factor, weight, ascending))
        return self

    def add_custom_factor(
        self, name: str, factor_fn: Callable[[Constituent], float], weight: float
    ) -> "CompositeScoreBuilder":
        """
        Add a custom factor with a calculation function.

        Args:
            name: Name of the custom factor
            factor_fn: Function that takes a Constituent and returns a score
            weight: Weight of the factor
        """
        self._custom_factors[name] = factor_fn
        self._custom_factor_weights[name] = weight
        return self

    def normalize(self, normalize: bool) -> "CompositeScoreBuilder":
        """Set whether to normalize factor values."""
        self._normalize = normalize
        return self

    def build(self) -> CompositeScore:
        """Build the CompositeScore object."""
        total_weight = sum(fw.weight for fw in self._factor_weights)
        total_weight += sum(self._custom_factor_weights.values())

        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Factor weights must sum to 1.0, got {total_weight}")

        return CompositeScore(
            factor_weights=self._factor_weights,
            normalize=self._normalize,
            custom_factors=self._custom_factors,
            custom_factor_weights=self._custom_factor_weights,
        )
