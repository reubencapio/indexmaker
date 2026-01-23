"""Tests for selection criteria."""

import pytest

from indexforge.core.constituent import Constituent
from indexforge.core.types import Factor
from indexforge.selection.composite import CompositeScore
from indexforge.selection.criteria import SelectionCriteria


class TestSelectionCriteria:
    """Tests for SelectionCriteria class."""

    def test_top_by_market_cap(self):
        """Test selecting top N by market cap."""
        criteria = SelectionCriteria.top_by_market_cap(3)

        candidates = [
            Constituent(ticker="A", market_cap=1e12),
            Constituent(ticker="B", market_cap=5e12),
            Constituent(ticker="C", market_cap=2e12),
            Constituent(ticker="D", market_cap=4e12),
            Constituent(ticker="E", market_cap=3e12),
        ]

        selected = criteria.select(candidates)

        assert len(selected) == 3
        selected_tickers = {c.ticker for c in selected}
        assert selected_tickers == {"B", "D", "E"}  # Top 3 by market cap

    def test_builder_basic(self):
        """Test basic builder usage."""
        criteria = SelectionCriteria.builder().ranking_by(Factor.MARKET_CAP).select_top(5).build()

        assert criteria.ranking_factor == Factor.MARKET_CAP
        assert criteria.select_count == 5

    def test_builder_with_buffer_rules(self):
        """Test builder with buffer rules."""
        criteria = (
            SelectionCriteria.builder()
            .ranking_by(Factor.MARKET_CAP)
            .select_top(10)
            .apply_buffer_rules(add_threshold=8, remove_threshold=12)
            .build()
        )

        assert criteria.buffer_rules is not None
        assert criteria.buffer_rules.add_threshold == 8
        assert criteria.buffer_rules.remove_threshold == 12

    def test_builder_with_diversification(self):
        """Test builder with diversification constraints."""
        criteria = (
            SelectionCriteria.builder()
            .ranking_by(Factor.MARKET_CAP)
            .select_top(20)
            .diversification_constraint(
                max_constituents_per_country=5, max_constituents_per_sector=8
            )
            .build()
        )

        assert criteria.diversification is not None
        assert criteria.diversification.max_constituents_per_country == 5
        assert criteria.diversification.max_constituents_per_sector == 8

    def test_invalid_select_count(self):
        """Test that invalid select count raises error."""
        with pytest.raises(ValueError):
            SelectionCriteria.builder().select_top(0).build()

        with pytest.raises(ValueError):
            SelectionCriteria.builder().select_top(-5).build()

    def test_custom_filter(self):
        """Test custom filter function."""
        criteria = (
            SelectionCriteria.builder()
            .ranking_by(Factor.MARKET_CAP)
            .select_top(10)
            .custom_filter(lambda c: c.sector == "Technology")
            .build()
        )

        candidates = [
            Constituent(ticker="AAPL", market_cap=3e12, sector="Technology"),
            Constituent(ticker="JPM", market_cap=0.5e12, sector="Financials"),
            Constituent(ticker="MSFT", market_cap=2.5e12, sector="Technology"),
        ]

        selected = criteria.select(candidates)

        assert len(selected) == 2
        assert all(c.sector == "Technology" for c in selected)

    def test_custom_ranking(self):
        """Test custom ranking function."""

        def innovation_score(c):
            # Custom scoring based on R&D (simulated)
            return c.market_cap * 0.5 + c.revenue * 0.5

        criteria = (
            SelectionCriteria.builder().custom_ranking(innovation_score).select_top(2).build()
        )

        candidates = [
            Constituent(ticker="A", market_cap=1e12, revenue=0.5e12),
            Constituent(ticker="B", market_cap=0.5e12, revenue=1e12),
            Constituent(ticker="C", market_cap=0.3e12, revenue=0.2e12),
        ]

        selected = criteria.select(candidates)

        assert len(selected) == 2

    def test_to_dict(self):
        """Test converting to dictionary."""
        criteria = (
            SelectionCriteria.builder()
            .ranking_by(Factor.MARKET_CAP)
            .select_top(50)
            .apply_buffer_rules(add_threshold=45, remove_threshold=60)
            .build()
        )

        data = criteria.to_dict()

        assert data["ranking_factor"] == "MARKET_CAP"
        assert data["select_count"] == 50
        assert data["buffer_rules"]["add_threshold"] == 45


class TestBufferRules:
    """Tests for buffer rules in selection."""

    def test_buffer_rules_keep_current(self):
        """Test that buffer rules help keep current constituents."""
        criteria = (
            SelectionCriteria.builder()
            .ranking_by(Factor.MARKET_CAP)
            .select_top(3)
            .apply_buffer_rules(add_threshold=2, remove_threshold=5)
            .build()
        )

        candidates = [
            Constituent(ticker="A", market_cap=5e12),
            Constituent(ticker="B", market_cap=4e12),
            Constituent(ticker="C", market_cap=3e12),
            Constituent(ticker="D", market_cap=2e12),
            Constituent(ticker="E", market_cap=1e12),
        ]

        # D is current constituent ranked 4th (within remove threshold of 5)
        current = [Constituent(ticker="D", market_cap=2e12)]

        selected = criteria.select(candidates, current)

        # D should be kept because rank 4 <= remove threshold 5
        selected_tickers = {c.ticker for c in selected}
        assert "D" in selected_tickers


class TestDiversificationConstraints:
    """Tests for diversification constraints."""

    def test_country_diversification(self):
        """Test country diversification constraint."""
        criteria = (
            SelectionCriteria.builder()
            .ranking_by(Factor.MARKET_CAP)
            .select_top(5)
            .diversification_constraint(max_constituents_per_country=2)
            .build()
        )

        candidates = [
            Constituent(ticker="A1", market_cap=5e12, country="US"),
            Constituent(ticker="A2", market_cap=4e12, country="US"),
            Constituent(ticker="A3", market_cap=3e12, country="US"),
            Constituent(ticker="B1", market_cap=2e12, country="UK"),
            Constituent(ticker="C1", market_cap=1e12, country="Germany"),
        ]

        selected = criteria.select(candidates)

        # Count US constituents
        us_count = sum(1 for c in selected if c.country == "US")
        assert us_count <= 2

    def test_sector_diversification(self):
        """Test sector diversification constraint."""
        criteria = (
            SelectionCriteria.builder()
            .ranking_by(Factor.MARKET_CAP)
            .select_top(4)
            .diversification_constraint(max_constituents_per_sector=2)
            .build()
        )

        candidates = [
            Constituent(ticker="AAPL", market_cap=3e12, sector="Technology"),
            Constituent(ticker="MSFT", market_cap=2.5e12, sector="Technology"),
            Constituent(ticker="GOOGL", market_cap=1.5e12, sector="Technology"),
            Constituent(ticker="JPM", market_cap=0.5e12, sector="Financials"),
            Constituent(ticker="BAC", market_cap=0.3e12, sector="Financials"),
        ]

        selected = criteria.select(candidates)

        # Count Technology constituents
        tech_count = sum(1 for c in selected if c.sector == "Technology")
        assert tech_count <= 2


class TestCompositeScore:
    """Tests for CompositeScore multi-factor selection."""

    def test_composite_score_basic(self):
        """Test basic composite score."""
        score = (
            CompositeScore.builder()
            .add_factor(Factor.MARKET_CAP, weight=0.6)
            .add_factor(Factor.DIVIDEND_YIELD, weight=0.4)
            .build()
        )

        constituent = Constituent(ticker="TEST", market_cap=1e12, dividend_yield=0.03)

        result = score.calculate(constituent)
        assert result > 0

    def test_composite_score_ranking(self):
        """Test ranking by composite score."""
        score = (
            CompositeScore.builder()
            .add_factor(Factor.MARKET_CAP, weight=0.5)
            .add_factor(Factor.DIVIDEND_YIELD, weight=0.5)
            .build()
        )

        constituents = [
            Constituent(ticker="A", market_cap=1e12, dividend_yield=0.05),
            Constituent(ticker="B", market_cap=2e12, dividend_yield=0.01),
            Constituent(ticker="C", market_cap=1.5e12, dividend_yield=0.03),
        ]

        ranked = score.rank(constituents)

        assert len(ranked) == 3
        assert ranked[0][0].ticker in ["A", "B", "C"]  # Just verify it returns valid data

    def test_composite_score_weights_must_sum_to_one(self):
        """Test that weights must sum to 1.0."""
        with pytest.raises(ValueError):
            (
                CompositeScore.builder()
                .add_factor(Factor.MARKET_CAP, weight=0.5)
                .add_factor(Factor.DIVIDEND_YIELD, weight=0.3)
                .build()  # Only sums to 0.8
            )

    def test_composite_with_custom_factor(self):
        """Test composite score with custom factor."""

        def innovation_factor(c):
            return c.revenue / c.market_cap if c.market_cap else 0

        score = (
            CompositeScore.builder()
            .add_factor(Factor.MARKET_CAP, weight=0.6)
            .add_custom_factor("innovation", innovation_factor, weight=0.4)
            .build()
        )

        constituent = Constituent(ticker="TEST", market_cap=1e12, revenue=0.1e12)

        result = score.calculate(constituent)
        assert result >= 0

    def test_selection_with_composite_score(self):
        """Test using composite score in selection criteria."""
        score = (
            CompositeScore.builder()
            .add_factor(Factor.MARKET_CAP, weight=0.7)
            .add_factor(Factor.DIVIDEND_YIELD, weight=0.3)
            .build()
        )

        criteria = SelectionCriteria.builder().composite_score(score).select_top(2).build()

        candidates = [
            Constituent(ticker="A", market_cap=1e12, dividend_yield=0.05),
            Constituent(ticker="B", market_cap=2e12, dividend_yield=0.01),
            Constituent(ticker="C", market_cap=0.5e12, dividend_yield=0.03),
        ]

        selected = criteria.select(candidates)

        assert len(selected) == 2
