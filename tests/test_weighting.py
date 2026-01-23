"""Tests for weighting methods."""

import pytest

from indexforge.core.constituent import Constituent
from indexforge.core.types import WeightingScheme
from indexforge.weighting.methods import WeightingMethod


class TestWeightingMethod:
    """Tests for WeightingMethod class."""

    def test_equal_weight(self):
        """Test equal weight method."""
        weighting = WeightingMethod.equal_weight()

        constituents = [
            Constituent(ticker="AAPL", market_cap=3e12),
            Constituent(ticker="MSFT", market_cap=2.5e12),
            Constituent(ticker="GOOGL", market_cap=1.5e12),
        ]

        weights = weighting.calculate_weights(constituents)

        assert len(weights) == 3
        assert abs(weights["AAPL"] - 1 / 3) < 0.001
        assert abs(weights["MSFT"] - 1 / 3) < 0.001
        assert abs(weights["GOOGL"] - 1 / 3) < 0.001
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_market_cap_weight(self):
        """Test market cap weighting."""
        weighting = WeightingMethod.market_cap().build()

        constituents = [
            Constituent(ticker="AAPL", market_cap=3e12),
            Constituent(ticker="MSFT", market_cap=2e12),
            Constituent(ticker="GOOGL", market_cap=1e12),
        ]

        weights = weighting.calculate_weights(constituents)

        # Total market cap is 6e12
        assert abs(weights["AAPL"] - 0.5) < 0.001  # 3/6
        assert abs(weights["MSFT"] - 1 / 3) < 0.001  # 2/6
        assert abs(weights["GOOGL"] - 1 / 6) < 0.001  # 1/6
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_market_cap_with_cap(self):
        """Test market cap weighting with maximum cap."""
        weighting = WeightingMethod.market_cap().with_cap(max_weight=0.40).build()

        constituents = [
            Constituent(ticker="AAPL", market_cap=3e12),
            Constituent(ticker="MSFT", market_cap=2e12),
            Constituent(ticker="GOOGL", market_cap=1e12),
        ]

        weights = weighting.calculate_weights(constituents)

        # AAPL should be capped at 40%
        assert weights["AAPL"] <= 0.40 + 0.001
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_free_float_market_cap(self):
        """Test free-float market cap weighting."""
        weighting = WeightingMethod.free_float_market_cap().build()

        constituents = [
            Constituent(ticker="AAPL", market_cap=3e12, free_float_market_cap=2.4e12),
            Constituent(ticker="MSFT", market_cap=2e12, free_float_market_cap=1.8e12),
            Constituent(ticker="GOOGL", market_cap=1e12, free_float_market_cap=0.8e12),
        ]

        weights = weighting.calculate_weights(constituents)

        # Weights should be based on free-float market cap
        total_ff = 2.4e12 + 1.8e12 + 0.8e12
        assert abs(weights["AAPL"] - 2.4e12 / total_ff) < 0.001
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_empty_constituents(self):
        """Test with empty constituent list."""
        weighting = WeightingMethod.equal_weight()
        weights = weighting.calculate_weights([])

        assert weights == {}

    def test_single_constituent(self):
        """Test with single constituent."""
        weighting = WeightingMethod.equal_weight()

        constituents = [Constituent(ticker="AAPL", market_cap=3e12)]
        weights = weighting.calculate_weights(constituents)

        assert weights["AAPL"] == 1.0

    def test_weighting_scheme_type(self):
        """Test weighting scheme property."""
        equal = WeightingMethod.equal_weight()
        market_cap = WeightingMethod.market_cap().build()

        assert equal.scheme == WeightingScheme.EQUAL_WEIGHT
        assert market_cap.scheme == WeightingScheme.MARKET_CAP

    def test_to_dict(self):
        """Test converting to dictionary."""
        weighting = WeightingMethod.market_cap().with_cap(max_weight=0.10).build()

        data = weighting.to_dict()

        assert data["scheme"] == "MARKET_CAP"
        assert data["caps"]["max_weight"] == 0.10


class TestWeightingMethodBuilder:
    """Tests for WeightingMethodBuilder class."""

    def test_builder_with_cap(self):
        """Test builder with weight cap."""
        weighting = WeightingMethod.market_cap().with_cap(max_weight=0.15).build()

        assert weighting.caps is not None
        assert weighting.caps.max_weight == 0.15

    def test_builder_with_multiple_caps(self):
        """Test builder with multiple caps."""
        weighting = (
            WeightingMethod.market_cap()
            .with_cap(max_weight=0.10)
            .with_cap(max_weight_per_sector=0.30)
            .with_cap(max_weight_per_country=0.40)
            .build()
        )

        assert weighting.caps.max_weight == 0.10
        assert weighting.caps.max_weight_per_sector == 0.30
        assert weighting.caps.max_weight_per_country == 0.40

    def test_builder_with_min_weight(self):
        """Test builder with minimum weight."""
        weighting = WeightingMethod.market_cap().with_min_weight(0.01).build()

        assert weighting.caps.min_weight == 0.01

    def test_invalid_max_weight(self):
        """Test that invalid max weight raises error."""
        with pytest.raises(ValueError):
            WeightingMethod.market_cap().with_cap(max_weight=1.5).build()

        with pytest.raises(ValueError):
            WeightingMethod.market_cap().with_cap(max_weight=0).build()

    def test_invalid_min_weight(self):
        """Test that invalid min weight raises error."""
        with pytest.raises(ValueError):
            WeightingMethod.market_cap().with_min_weight(1.0).build()

        with pytest.raises(ValueError):
            WeightingMethod.market_cap().with_min_weight(-0.1).build()


class TestCustomWeighting:
    """Tests for custom weighting functions."""

    def test_custom_weighting(self):
        """Test custom weighting function."""

        def equal_weights(constituents):
            n = len(constituents)
            return {c.ticker: 1.0 / n for c in constituents}

        weighting = WeightingMethod.custom(equal_weights)

        constituents = [
            Constituent(ticker="AAPL"),
            Constituent(ticker="MSFT"),
        ]

        weights = weighting.calculate_weights(constituents)

        assert weights["AAPL"] == 0.5
        assert weights["MSFT"] == 0.5

    def test_custom_weighting_by_dividend_yield(self):
        """Test custom weighting by dividend yield."""

        def dividend_weights(constituents):
            total_div = sum(c.dividend_yield for c in constituents)
            if total_div == 0:
                return {c.ticker: 1.0 / len(constituents) for c in constituents}
            return {c.ticker: c.dividend_yield / total_div for c in constituents}

        weighting = WeightingMethod.custom(dividend_weights)

        constituents = [
            Constituent(ticker="HIGH", dividend_yield=0.04),
            Constituent(ticker="LOW", dividend_yield=0.01),
        ]

        weights = weighting.calculate_weights(constituents)

        assert weights["HIGH"] == 0.8  # 4/5
        assert weights["LOW"] == 0.2  # 1/5


class TestSectorCountryWeighting:
    """Tests for sector and country weight caps."""

    def test_sector_cap(self):
        """Test sector weight cap."""
        weighting = WeightingMethod.market_cap().with_cap(max_weight_per_sector=0.50).build()

        constituents = [
            Constituent(ticker="AAPL", market_cap=3e12, sector="Technology"),
            Constituent(ticker="MSFT", market_cap=2.5e12, sector="Technology"),
            Constituent(ticker="JPM", market_cap=0.5e12, sector="Financials"),
        ]

        weights = weighting.calculate_weights(constituents)

        # Technology sector weight (AAPL + MSFT) should be capped
        tech_weight = weights["AAPL"] + weights["MSFT"]
        assert tech_weight <= 0.50 + 0.01

    def test_country_cap(self):
        """Test country weight cap."""
        weighting = WeightingMethod.market_cap().with_cap(max_weight_per_country=0.60).build()

        constituents = [
            Constituent(ticker="AAPL", market_cap=3e12, country="US"),
            Constituent(ticker="MSFT", market_cap=2e12, country="US"),
            Constituent(ticker="SAP", market_cap=0.5e12, country="Germany"),
        ]

        weights = weighting.calculate_weights(constituents)

        # US weight should be capped
        us_weight = weights["AAPL"] + weights["MSFT"]
        assert us_weight <= 0.60 + 0.01
