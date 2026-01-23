"""
Weighting methods for index constituents.

Defines how constituents are weighted within an index.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from indexforge.core.constituent import Constituent
from indexforge.core.types import Factor, WeightingScheme


@dataclass
class WeightCaps:
    """Weight capping constraints."""

    max_weight: Optional[float] = None  # Max weight per constituent
    max_weight_per_issuer: Optional[float] = None  # Max weight per issuer
    max_weight_per_sector: Optional[float] = None  # Max weight per sector
    max_weight_per_country: Optional[float] = None  # Max weight per country
    min_weight: Optional[float] = None  # Minimum weight per constituent


@dataclass
class WeightingMethod:
    """
    Defines how index constituents are weighted.

    Supports various weighting schemes including equal weight,
    market cap, free-float, and factor-based weighting.

    Attributes:
        scheme: The weighting scheme type
        factor: Factor used for factor-based weighting
        caps: Weight capping constraints

    Example:
        >>> weighting = WeightingMethod.market_cap()
        >>> weighting = WeightingMethod.equal_weight()
        >>> weighting = (WeightingMethod.market_cap()
        ...     .with_cap(max_weight=0.10)
        ...     .build()
        ... )
    """

    scheme: WeightingScheme = WeightingScheme.MARKET_CAP
    factor: Optional[Factor] = None
    caps: Optional[WeightCaps] = None
    custom_weighting: Optional[Callable[[list[Constituent]], dict[str, float]]] = None

    @staticmethod
    def equal_weight() -> "WeightingMethod":
        """
        Create equal weight method.

        Each constituent receives the same weight (1/N).

        Returns:
            WeightingMethod configured for equal weighting
        """
        return WeightingMethod(scheme=WeightingScheme.EQUAL_WEIGHT)

    @staticmethod
    def market_cap() -> "WeightingMethodBuilder":
        """
        Create market cap weighted method builder.

        Constituents are weighted by their market capitalization.

        Returns:
            WeightingMethodBuilder for further configuration
        """
        return WeightingMethodBuilder(scheme=WeightingScheme.MARKET_CAP)

    @staticmethod
    def free_float_market_cap() -> "WeightingMethodBuilder":
        """
        Create free-float market cap weighted method builder.

        Constituents are weighted by free-float adjusted market cap.

        Returns:
            WeightingMethodBuilder for further configuration
        """
        return WeightingMethodBuilder(scheme=WeightingScheme.FREE_FLOAT_MARKET_CAP)

    @staticmethod
    def factor_based(factor: Factor) -> "WeightingMethodBuilder":
        """
        Create factor-based weighting method builder.

        Args:
            factor: The factor to use for weighting

        Returns:
            WeightingMethodBuilder for further configuration
        """
        builder = WeightingMethodBuilder(scheme=WeightingScheme.FACTOR_BASED)
        builder._factor = factor
        return builder

    @staticmethod
    def custom(weighting_fn: Callable[[list[Constituent]], dict[str, float]]) -> "WeightingMethod":
        """
        Create custom weighting method.

        Args:
            weighting_fn: Function that takes constituents and returns weights

        Returns:
            WeightingMethod with custom logic
        """
        return WeightingMethod(
            scheme=WeightingScheme.CUSTOM,
            custom_weighting=weighting_fn,
        )

    def calculate_weights(self, constituents: list[Constituent]) -> dict[str, float]:
        """
        Calculate weights for a list of constituents.

        Args:
            constituents: List of constituents to weight

        Returns:
            Dictionary mapping ticker to weight
        """
        if not constituents:
            return {}

        # Calculate raw weights based on scheme
        if self.scheme == WeightingScheme.EQUAL_WEIGHT:
            weights = self._calculate_equal_weights(constituents)
        elif self.scheme == WeightingScheme.MARKET_CAP:
            weights = self._calculate_market_cap_weights(constituents)
        elif self.scheme == WeightingScheme.FREE_FLOAT_MARKET_CAP:
            weights = self._calculate_free_float_weights(constituents)
        elif self.scheme == WeightingScheme.FACTOR_BASED:
            weights = self._calculate_factor_weights(constituents)
        elif self.scheme == WeightingScheme.CUSTOM and self.custom_weighting:
            weights = self.custom_weighting(constituents)
        else:
            weights = self._calculate_equal_weights(constituents)

        # Apply caps and normalize
        if self.caps:
            weights = self._apply_caps(weights, constituents)

        # Final normalization
        weights = self._normalize(weights)

        return weights

    def _calculate_equal_weights(self, constituents: list[Constituent]) -> dict[str, float]:
        """Calculate equal weights."""
        n = len(constituents)
        weight = 1.0 / n if n > 0 else 0.0
        return {c.ticker: weight for c in constituents}

    def _calculate_market_cap_weights(self, constituents: list[Constituent]) -> dict[str, float]:
        """Calculate market cap weights."""
        total_cap = sum(c.market_cap for c in constituents)
        if total_cap == 0:
            return self._calculate_equal_weights(constituents)
        return {c.ticker: c.market_cap / total_cap for c in constituents}

    def _calculate_free_float_weights(self, constituents: list[Constituent]) -> dict[str, float]:
        """Calculate free-float adjusted market cap weights."""
        total_ff_cap = sum(c.free_float_market_cap or c.market_cap for c in constituents)
        if total_ff_cap == 0:
            return self._calculate_equal_weights(constituents)
        return {
            c.ticker: (c.free_float_market_cap or c.market_cap) / total_ff_cap for c in constituents
        }

    def _calculate_factor_weights(self, constituents: list[Constituent]) -> dict[str, float]:
        """Calculate factor-based weights."""
        if not self.factor:
            return self._calculate_equal_weights(constituents)

        factor_values = {}
        for c in constituents:
            value = self._get_factor_value(c, self.factor)
            if value and value > 0:
                factor_values[c.ticker] = value

        total = sum(factor_values.values())
        if total == 0:
            return self._calculate_equal_weights(constituents)

        return {ticker: value / total for ticker, value in factor_values.items()}

    def _get_factor_value(self, constituent: Constituent, factor: Factor) -> Optional[float]:
        """Get factor value for a constituent."""
        factor_mapping = {
            Factor.MARKET_CAP: constituent.market_cap,
            Factor.FREE_FLOAT_MARKET_CAP: constituent.free_float_market_cap,
            Factor.LIQUIDITY: constituent.average_daily_volume,
            Factor.VOLUME: constituent.average_daily_volume,
            Factor.DIVIDEND_YIELD: constituent.dividend_yield,
        }
        return factor_mapping.get(factor)

    def _apply_caps(
        self, weights: dict[str, float], constituents: list[Constituent]
    ) -> dict[str, float]:
        """Apply weight caps with iterative redistribution."""
        if not self.caps:
            return weights

        caps = self.caps
        constituent_lookup = {c.ticker: c for c in constituents}

        # Apply per-constituent cap
        if caps.max_weight:
            weights = self._apply_single_cap(weights, caps.max_weight)

        # Apply sector caps
        if caps.max_weight_per_sector:
            weights = self._apply_group_cap(
                weights, constituent_lookup, lambda c: c.sector, caps.max_weight_per_sector
            )

        # Apply country caps
        if caps.max_weight_per_country:
            weights = self._apply_group_cap(
                weights, constituent_lookup, lambda c: c.country, caps.max_weight_per_country
            )

        # Apply minimum weight
        if caps.min_weight:
            for ticker in weights:
                if weights[ticker] < caps.min_weight:
                    weights[ticker] = caps.min_weight

        return weights

    def _apply_single_cap(
        self, weights: dict[str, float], max_weight: float, iterations: int = 10
    ) -> dict[str, float]:
        """Apply maximum weight cap with redistribution."""
        for _ in range(iterations):
            excess = 0.0
            uncapped_weight = 0.0
            uncapped_tickers = []

            for ticker, weight in weights.items():
                if weight > max_weight:
                    excess += weight - max_weight
                    weights[ticker] = max_weight
                else:
                    uncapped_weight += weight
                    uncapped_tickers.append(ticker)

            if excess == 0 or not uncapped_tickers:
                break

            # Redistribute excess proportionally
            for ticker in uncapped_tickers:
                if uncapped_weight > 0:
                    weights[ticker] += excess * (weights[ticker] / uncapped_weight)

        return weights

    def _apply_group_cap(
        self,
        weights: dict[str, float],
        constituents: dict[str, Constituent],
        group_fn: Callable[[Constituent], str],
        max_weight: float,
        iterations: int = 10,
    ) -> dict[str, float]:
        """Apply group-level weight cap with iterative redistribution."""
        for _ in range(iterations):
            # Calculate group weights
            group_weights: dict[str, float] = {}
            for ticker, weight in weights.items():
                if ticker in constituents:
                    group = group_fn(constituents[ticker])
                    group_weights[group] = group_weights.get(group, 0) + weight

            # Find excess and scale down overweight groups
            total_excess = 0.0
            for group, group_weight in group_weights.items():
                if group_weight > max_weight:
                    scale_factor = max_weight / group_weight
                    for ticker in list(weights.keys()):
                        if ticker in constituents:
                            if group_fn(constituents[ticker]) == group:
                                old_weight = weights[ticker]
                                weights[ticker] *= scale_factor
                                total_excess += old_weight - weights[ticker]

            if total_excess == 0:
                break

            # Redistribute excess to underweight groups
            underweight_groups = {g: w for g, w in group_weights.items() if w < max_weight}
            if underweight_groups:
                underweight_total = sum(underweight_groups.values())
                for ticker in weights:
                    if ticker in constituents:
                        group = group_fn(constituents[ticker])
                        if group in underweight_groups and underweight_total > 0:
                            proportion = weights[ticker] / underweight_total
                            weights[ticker] += total_excess * proportion

        return weights

    def _normalize(self, weights: dict[str, float]) -> dict[str, float]:
        """Normalize weights to sum to 1.0."""
        total = sum(weights.values())
        if total == 0:
            return weights
        return {ticker: weight / total for ticker, weight in weights.items()}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "scheme": str(self.scheme),
            "factor": str(self.factor) if self.factor else None,
            "caps": (
                {
                    "max_weight": self.caps.max_weight,
                    "max_weight_per_sector": self.caps.max_weight_per_sector,
                    "max_weight_per_country": self.caps.max_weight_per_country,
                }
                if self.caps
                else None
            ),
        }


class WeightingMethodBuilder:
    """
    Builder for constructing WeightingMethod with fluent syntax.

    Example:
        >>> weighting = (WeightingMethod.market_cap()
        ...     .with_cap(max_weight=0.10)
        ...     .with_cap(max_weight_per_sector=0.30)
        ...     .build()
        ... )
    """

    def __init__(self, scheme: WeightingScheme = WeightingScheme.MARKET_CAP) -> None:
        self._scheme: WeightingScheme = scheme
        self._factor: Optional[Factor] = None
        self._max_weight: Optional[float] = None
        self._max_weight_per_issuer: Optional[float] = None
        self._max_weight_per_sector: Optional[float] = None
        self._max_weight_per_country: Optional[float] = None
        self._min_weight: Optional[float] = None

    def with_cap(
        self,
        max_weight: Optional[float] = None,
        max_weight_per_issuer: Optional[float] = None,
        max_weight_per_sector: Optional[float] = None,
        max_weight_per_country: Optional[float] = None,
    ) -> "WeightingMethodBuilder":
        """
        Set weight caps.

        Args:
            max_weight: Maximum weight per constituent (e.g., 0.10 for 10%)
            max_weight_per_issuer: Maximum weight per issuer
            max_weight_per_sector: Maximum weight per sector
            max_weight_per_country: Maximum weight per country
        """
        if max_weight is not None:
            if not 0.0 < max_weight <= 1.0:
                raise ValueError("max_weight must be between 0 and 1")
            self._max_weight = max_weight
        if max_weight_per_issuer is not None:
            self._max_weight_per_issuer = max_weight_per_issuer
        if max_weight_per_sector is not None:
            self._max_weight_per_sector = max_weight_per_sector
        if max_weight_per_country is not None:
            self._max_weight_per_country = max_weight_per_country
        return self

    def with_min_weight(self, min_weight: float) -> "WeightingMethodBuilder":
        """Set minimum weight per constituent."""
        if not 0.0 <= min_weight < 1.0:
            raise ValueError("min_weight must be between 0 and 1")
        self._min_weight = min_weight
        return self

    def factor(self, factor: Factor) -> "WeightingMethodBuilder":
        """Set the factor for factor-based weighting."""
        self._factor = factor
        return self

    def build(self) -> WeightingMethod:
        """Build the WeightingMethod object."""
        caps = None
        if any(
            [
                self._max_weight,
                self._max_weight_per_issuer,
                self._max_weight_per_sector,
                self._max_weight_per_country,
                self._min_weight,
            ]
        ):
            caps = WeightCaps(
                max_weight=self._max_weight,
                max_weight_per_issuer=self._max_weight_per_issuer,
                max_weight_per_sector=self._max_weight_per_sector,
                max_weight_per_country=self._max_weight_per_country,
                min_weight=self._min_weight,
            )

        return WeightingMethod(
            scheme=self._scheme,
            factor=self._factor,
            caps=caps,
        )
