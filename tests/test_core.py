"""Tests for core domain models."""

import pytest

from indexforge.core.constituent import Constituent
from indexforge.core.index import Index
from indexforge.core.types import AssetClass, Currency, Region
from indexforge.core.universe import Universe


class TestCurrency:
    """Tests for Currency enum."""

    def test_currency_values(self):
        """Test that currency values are correct."""
        assert Currency.USD.value == "USD"
        assert Currency.EUR.value == "EUR"
        assert Currency.GBP.value == "GBP"

    def test_currency_string(self):
        """Test string conversion."""
        assert str(Currency.USD) == "USD"


class TestConstituent:
    """Tests for Constituent model."""

    def test_create_constituent(self):
        """Test creating a constituent."""
        constituent = Constituent(
            ticker="AAPL", name="Apple Inc.", weight=0.10, shares=1000, price=150.0
        )

        assert constituent.ticker == "AAPL"
        assert constituent.name == "Apple Inc."
        assert constituent.weight == 0.10
        assert constituent.shares == 1000
        assert constituent.price == 150.0

    def test_market_value(self):
        """Test market value calculation."""
        constituent = Constituent(ticker="AAPL", shares=100, price=150.0)

        assert constituent.market_value == 15000.0

    def test_constituent_equality(self):
        """Test constituent equality by ticker."""
        c1 = Constituent(ticker="AAPL", name="Apple")
        c2 = Constituent(ticker="AAPL", name="Apple Inc.")
        c3 = Constituent(ticker="MSFT", name="Microsoft")

        assert c1 == c2
        assert c1 != c3

    def test_constituent_hash(self):
        """Test constituent hashing."""
        c1 = Constituent(ticker="AAPL")
        c2 = Constituent(ticker="AAPL")

        assert hash(c1) == hash(c2)

    def test_to_dict(self):
        """Test converting to dictionary."""
        constituent = Constituent(
            ticker="AAPL", name="Apple Inc.", weight=0.10, market_cap=3000000000000
        )

        data = constituent.to_dict()

        assert data["ticker"] == "AAPL"
        assert data["name"] == "Apple Inc."
        assert data["weight"] == 0.10

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {"ticker": "AAPL", "name": "Apple Inc.", "weight": 0.10, "market_cap": 3000000000000}

        constituent = Constituent.from_dict(data)

        assert constituent.ticker == "AAPL"
        assert constituent.name == "Apple Inc."


class TestUniverse:
    """Tests for Universe model."""

    def test_from_tickers(self):
        """Test creating universe from tickers."""
        universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL"])

        assert universe.tickers == ["AAPL", "MSFT", "GOOGL"]
        assert universe.asset_class == AssetClass.EQUITIES

    def test_builder_basic(self):
        """Test basic builder usage."""
        universe = (
            Universe.builder()
            .asset_class(AssetClass.EQUITIES)
            .regions([Region.NORTH_AMERICA])
            .build()
        )

        assert universe.asset_class == AssetClass.EQUITIES
        assert universe.regions == [Region.NORTH_AMERICA]

    def test_builder_with_filters(self):
        """Test builder with all filters."""
        universe = (
            Universe.builder()
            .asset_class(AssetClass.EQUITIES)
            .regions([Region.NORTH_AMERICA, Region.EUROPE])
            .sectors(["Technology", "Healthcare"])
            .min_market_cap(1_000_000_000)
            .min_free_float(0.15)
            .build()
        )

        assert universe.min_market_cap == 1_000_000_000
        assert universe.min_free_float == 0.15
        assert "Technology" in universe.sectors

    def test_builder_min_free_float_validation(self):
        """Test that free float must be between 0 and 1."""
        with pytest.raises(ValueError):
            Universe.builder().min_free_float(1.5).build()

        with pytest.raises(ValueError):
            Universe.builder().min_free_float(-0.1).build()

    def test_is_eligible_by_ticker(self):
        """Test eligibility by ticker list."""
        universe = Universe.from_tickers(["AAPL", "MSFT"])

        aapl = Constituent(ticker="AAPL")
        googl = Constituent(ticker="GOOGL")

        assert universe.is_eligible(aapl)
        assert not universe.is_eligible(googl)

    def test_is_eligible_by_market_cap(self):
        """Test eligibility by market cap."""
        universe = Universe.builder().min_market_cap(1_000_000_000).build()

        big_company = Constituent(ticker="BIG", market_cap=5_000_000_000)
        small_company = Constituent(ticker="SMALL", market_cap=100_000_000)

        assert universe.is_eligible(big_company)
        assert not universe.is_eligible(small_company)

    def test_filter_constituents(self):
        """Test filtering constituents."""
        universe = Universe.from_tickers(["AAPL", "MSFT"])

        constituents = [
            Constituent(ticker="AAPL"),
            Constituent(ticker="MSFT"),
            Constituent(ticker="GOOGL"),
        ]

        filtered = universe.filter(constituents)

        assert len(filtered) == 2
        assert all(c.ticker in ["AAPL", "MSFT"] for c in filtered)

    def test_to_dict(self):
        """Test converting to dictionary."""
        universe = (
            Universe.builder()
            .asset_class(AssetClass.EQUITIES)
            .min_market_cap(1_000_000_000)
            .build()
        )

        data = universe.to_dict()

        assert data["asset_class"] == "EQUITIES"
        assert data["min_market_cap"] == 1_000_000_000


class TestIndex:
    """Tests for Index model."""

    def test_create_index(self):
        """Test creating an index."""
        index = Index.create(
            name="Test Index",
            identifier="TEST",
            currency=Currency.USD,
            base_date="2025-01-01",
            base_value=1000.0,
        )

        assert index.name == "Test Index"
        assert index.identifier == "TEST"
        assert index.currency == Currency.USD
        assert index.base_value == 1000.0

    def test_create_index_with_string_currency(self):
        """Test creating index with string currency."""
        index = Index.create(
            name="Test",
            identifier="TEST",
            currency="EUR",
            base_date="2025-01-01",
            base_value=1000.0,
        )

        assert index.currency == Currency.EUR

    def test_set_universe(self):
        """Test setting universe."""
        index = Index.create(
            name="Test",
            identifier="TEST",
            currency=Currency.USD,
            base_date="2025-01-01",
            base_value=1000.0,
        )

        universe = Universe.from_tickers(["AAPL", "MSFT"])
        result = index.set_universe(universe)

        # Should return self for chaining
        assert result is index

    def test_method_chaining(self):
        """Test that configuration methods can be chained."""
        from indexforge.rebalancing.schedule import RebalancingSchedule
        from indexforge.weighting.methods import WeightingMethod

        index = (
            Index.create(
                name="Test",
                identifier="TEST",
                currency=Currency.USD,
                base_date="2025-01-01",
                base_value=1000.0,
            )
            .set_universe(Universe.from_tickers(["AAPL"]))
            .set_weighting_method(WeightingMethod.equal_weight())
            .set_rebalancing_schedule(RebalancingSchedule.quarterly())
        )

        assert index.name == "Test"

    def test_validate_missing_universe(self):
        """Test validation fails without universe."""
        index = Index.create(
            name="Test",
            identifier="TEST",
            currency=Currency.USD,
            base_date="2025-01-01",
            base_value=1000.0,
        )

        report = index.validate()

        assert not report.is_valid
        assert any("universe" in e.field for e in report.errors)

    def test_to_dict(self):
        """Test converting to dictionary."""
        index = Index.create(
            name="Test Index",
            identifier="TEST",
            currency=Currency.USD,
            base_date="2025-01-01",
            base_value=1000.0,
        )
        index.set_universe(Universe.from_tickers(["AAPL", "MSFT"]))

        data = index.to_dict()

        assert data["name"] == "Test Index"
        assert data["identifier"] == "TEST"
        assert data["currency"] == "USD"
        assert data["base_value"] == 1000.0

    def test_index_string_representation(self):
        """Test string representation."""
        index = Index.create(
            name="Test Index",
            identifier="TEST",
            currency=Currency.USD,
            base_date="2025-01-01",
            base_value=1000.0,
        )

        assert "Test Index" in str(index)
        assert "TEST" in str(index)
