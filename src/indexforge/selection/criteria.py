"""
Selection criteria for index constituent selection.

Defines how constituents are selected from the investment universe.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from indexforge.core.constituent import Constituent
from indexforge.core.types import Factor
from indexforge.selection.composite import CompositeScore


@dataclass
class BufferRules:
    """
    Buffer rules for reducing index turnover.

    Buffer rules prevent excessive changes at rebalancing by requiring
    securities to rank significantly higher/lower before being added/removed.
    """

    add_threshold: Optional[int] = None  # Must rank at least this to be added
    remove_threshold: Optional[int] = None  # Must rank worse than this to be removed


@dataclass
class DiversificationConstraints:
    """Constraints to ensure diversification."""

    max_constituents_per_country: Optional[int] = None
    max_constituents_per_sector: Optional[int] = None
    max_constituents_per_issuer: Optional[int] = None


@dataclass
class SelectionCriteria:
    """
    Criteria for selecting index constituents.

    Defines how securities are ranked and selected from the universe.

    Attributes:
        ranking_factor: Primary factor for ranking
        select_count: Number of constituents to select
        composite_score: Multi-factor scoring (alternative to single factor)
        buffer_rules: Rules to reduce turnover
        diversification: Diversification constraints

    Example:
        >>> criteria = (SelectionCriteria.builder()
        ...     .ranking_by(Factor.MARKET_CAP)
        ...     .select_top(50)
        ...     .apply_buffer_rules(add_threshold=45, remove_threshold=60)
        ...     .build()
        ... )
    """

    ranking_factor: Optional[Factor] = None
    composite_score: Optional[CompositeScore] = None
    select_count: int = 50
    buffer_rules: Optional[BufferRules] = None
    diversification: Optional[DiversificationConstraints] = None
    custom_ranking: Optional[Callable[[Constituent], float]] = None
    custom_filters: list[Callable[[Constituent], bool]] = field(default_factory=list)

    @staticmethod
    def builder() -> "SelectionCriteriaBuilder":
        """Create a new SelectionCriteriaBuilder."""
        return SelectionCriteriaBuilder()

    @staticmethod
    def top_by_market_cap(n: int) -> "SelectionCriteria":
        """
        Convenience method to select top N by market cap.

        Args:
            n: Number of constituents to select

        Returns:
            SelectionCriteria configured for market cap selection
        """
        return SelectionCriteria(
            ranking_factor=Factor.MARKET_CAP,
            select_count=n,
        )

    def select(
        self,
        candidates: list[Constituent],
        current_constituents: Optional[list[Constituent]] = None,
    ) -> list[Constituent]:
        """
        Select constituents based on the criteria.

        Args:
            candidates: List of candidate constituents
            current_constituents: Current index constituents (for buffer rules)

        Returns:
            List of selected constituents
        """
        # Apply custom filters first
        filtered = candidates
        for filter_fn in self.custom_filters:
            filtered = [c for c in filtered if filter_fn(c)]

        # Rank the candidates
        ranked = self._rank(filtered)

        # Apply buffer rules if we have current constituents
        if self.buffer_rules and current_constituents:
            selected = self._apply_buffer_rules(ranked, current_constituents)
        else:
            # Simple top N selection
            selected = [c for c, _ in ranked[: self.select_count]]

        # Apply diversification constraints
        if self.diversification:
            selected = self._apply_diversification(selected, ranked)

        return selected

    def _rank(self, constituents: list[Constituent]) -> list[tuple[Constituent, float]]:
        """Rank constituents by the specified criteria."""
        if self.composite_score:
            return self.composite_score.rank(constituents)

        if self.custom_ranking:
            scored = [(c, self.custom_ranking(c)) for c in constituents]
            return sorted(scored, key=lambda x: x[1], reverse=True)

        if self.ranking_factor:
            scored = [
                (c, self._get_factor_value(c, self.ranking_factor) or 0.0) for c in constituents
            ]
            return sorted(scored, key=lambda x: x[1], reverse=True)

        # Default: rank by market cap
        scored = [(c, c.market_cap) for c in constituents]
        return sorted(scored, key=lambda x: x[1], reverse=True)

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
        }
        return factor_mapping.get(factor)

    def _apply_buffer_rules(
        self, ranked: list[tuple[Constituent, float]], current: list[Constituent]
    ) -> list[Constituent]:
        """Apply buffer rules to selection."""
        if not self.buffer_rules:
            return [c for c, _ in ranked[: self.select_count]]

        current_tickers = {c.ticker for c in current}
        selected: list[Constituent] = []

        # Create rank lookup
        {c.ticker: i + 1 for i, (c, _) in enumerate(ranked)}

        add_threshold = self.buffer_rules.add_threshold or self.select_count
        remove_threshold = self.buffer_rules.remove_threshold or self.select_count

        # Process candidates
        for i, (constituent, score) in enumerate(ranked):
            rank = i + 1
            is_current = constituent.ticker in current_tickers

            if is_current:
                # Keep if ranked within remove threshold
                if rank <= remove_threshold:
                    selected.append(constituent)
            else:
                # Add if ranked within add threshold
                if rank <= add_threshold and len(selected) < self.select_count:
                    selected.append(constituent)

            if len(selected) >= self.select_count:
                break

        return selected[: self.select_count]

    def _apply_diversification(
        self, selected: list[Constituent], ranked: list[tuple[Constituent, float]]
    ) -> list[Constituent]:
        """Apply diversification constraints."""
        if not self.diversification:
            return selected

        div = self.diversification
        final: list[Constituent] = []

        country_counts: dict[str, int] = {}
        sector_counts: dict[str, int] = {}

        # First pass: add constituents respecting constraints
        for constituent in selected:
            country = constituent.country
            sector = constituent.sector

            # Check country constraint
            if div.max_constituents_per_country:
                if country_counts.get(country, 0) >= div.max_constituents_per_country:
                    continue

            # Check sector constraint
            if div.max_constituents_per_sector:
                if sector_counts.get(sector, 0) >= div.max_constituents_per_sector:
                    continue

            final.append(constituent)
            country_counts[country] = country_counts.get(country, 0) + 1
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        # If we don't have enough, add from ranked list
        if len(final) < self.select_count:
            selected_tickers = {c.ticker for c in final}
            for constituent, _ in ranked:
                if constituent.ticker in selected_tickers:
                    continue

                country = constituent.country
                sector = constituent.sector

                # Check constraints
                country_ok = (
                    not div.max_constituents_per_country
                    or country_counts.get(country, 0) < div.max_constituents_per_country
                )
                sector_ok = (
                    not div.max_constituents_per_sector
                    or sector_counts.get(sector, 0) < div.max_constituents_per_sector
                )

                if country_ok and sector_ok:
                    final.append(constituent)
                    country_counts[country] = country_counts.get(country, 0) + 1
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1

                if len(final) >= self.select_count:
                    break

        return final

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "ranking_factor": str(self.ranking_factor) if self.ranking_factor else None,
            "select_count": self.select_count,
            "buffer_rules": (
                {
                    "add_threshold": self.buffer_rules.add_threshold,
                    "remove_threshold": self.buffer_rules.remove_threshold,
                }
                if self.buffer_rules
                else None
            ),
        }


class SelectionCriteriaBuilder:
    """
    Builder for constructing SelectionCriteria with fluent syntax.

    Example:
        >>> criteria = (SelectionCriteria.builder()
        ...     .ranking_by(Factor.MARKET_CAP)
        ...     .select_top(50)
        ...     .apply_buffer_rules(add_threshold=45, remove_threshold=60)
        ...     .diversification_constraint(max_constituents_per_country=15)
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        self._ranking_factor: Optional[Factor] = None
        self._composite_score: Optional[CompositeScore] = None
        self._select_count: int = 50
        self._buffer_rules: Optional[BufferRules] = None
        self._diversification: Optional[DiversificationConstraints] = None
        self._custom_ranking: Optional[Callable[[Constituent], float]] = None
        self._custom_filters: list[Callable[[Constituent], bool]] = []

    def ranking_by(self, factor: Factor) -> "SelectionCriteriaBuilder":
        """Set the primary ranking factor."""
        self._ranking_factor = factor
        return self

    def composite_score(self, score: CompositeScore) -> "SelectionCriteriaBuilder":
        """Set a composite score for multi-factor ranking."""
        self._composite_score = score
        return self

    def select_top(self, n: int) -> "SelectionCriteriaBuilder":
        """Set the number of constituents to select."""
        if n <= 0:
            raise ValueError("Select count must be positive")
        self._select_count = n
        return self

    def apply_buffer_rules(
        self, add_threshold: Optional[int] = None, remove_threshold: Optional[int] = None
    ) -> "SelectionCriteriaBuilder":
        """
        Apply buffer rules to reduce turnover.

        Args:
            add_threshold: Rank required to be added to index
            remove_threshold: Rank at which constituent is removed
        """
        self._buffer_rules = BufferRules(
            add_threshold=add_threshold,
            remove_threshold=remove_threshold,
        )
        return self

    def diversification_constraint(
        self,
        max_constituents_per_country: Optional[int] = None,
        max_constituents_per_sector: Optional[int] = None,
        max_constituents_per_issuer: Optional[int] = None,
    ) -> "SelectionCriteriaBuilder":
        """Add diversification constraints."""
        self._diversification = DiversificationConstraints(
            max_constituents_per_country=max_constituents_per_country,
            max_constituents_per_sector=max_constituents_per_sector,
            max_constituents_per_issuer=max_constituents_per_issuer,
        )
        return self

    def custom_ranking(
        self, ranking_fn: Callable[[Constituent], float]
    ) -> "SelectionCriteriaBuilder":
        """Set a custom ranking function."""
        self._custom_ranking = ranking_fn
        return self

    def theme_filter(
        self,
        keywords: list[str],
        match_mode: str = "any",
        case_sensitive: bool = False,
    ) -> "SelectionCriteriaBuilder":
        """
        Add theme-based filter by keywords in business description.

        Filters constituents based on keywords found in their business
        descriptions, industry, or company name.

        Args:
            keywords: Keywords to search for
            match_mode: "any" (match at least one) or "all" (match all)
            case_sensitive: Whether matching is case-sensitive

        Example:
            >>> criteria = (SelectionCriteria.builder()
            ...     .theme_filter(["quantum", "qubit"])
            ...     .select_top(20)
            ...     .build()
            ... )
        """
        from indexforge.selection.theme import create_theme_filter

        return self.custom_filter(create_theme_filter(keywords, match_mode, case_sensitive))

    def custom_filter(self, filter_fn: Callable[[Constituent], bool]) -> "SelectionCriteriaBuilder":
        """Add a custom filter function."""
        self._custom_filters.append(filter_fn)
        return self

    def build(self) -> SelectionCriteria:
        """Build the SelectionCriteria object."""
        return SelectionCriteria(
            ranking_factor=self._ranking_factor,
            composite_score=self._composite_score,
            select_count=self._select_count,
            buffer_rules=self._buffer_rules,
            diversification=self._diversification,
            custom_ranking=self._custom_ranking,
            custom_filters=self._custom_filters,
        )
