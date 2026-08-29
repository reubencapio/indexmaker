"""
Tests for the factor registry.

These pin the behaviour that used to fail silently: an unsupported factor scored
every constituent 0.0 and the "ranking" became input order, and ranking on a
valuation ratio put the most expensive companies first.
"""

import pytest

from indexforge import Constituent, Factor, SelectionCriteria
from indexforge.data.connectors.openbb import OpenBBConnector
from indexforge.data.connectors.yahoo import YahooFinanceConnector
from indexforge.selection.factors import (
    FACTOR_REGISTRY,
    SUPPORTED_FACTORS,
    UNSUPPORTED_FACTORS,
    UnsupportedFactorError,
    is_supported,
    missing_requirements,
    resolve_factor,
)


def _constituent(ticker: str, **kwargs) -> Constituent:
    return Constituent(ticker=ticker, name=ticker, **kwargs)


class TestRegistryShape:
    def test_supported_and_unsupported_partition_the_enum(self):
        assert SUPPORTED_FACTORS | UNSUPPORTED_FACTORS == set(Factor)
        assert not (SUPPORTED_FACTORS & UNSUPPORTED_FACTORS)

    def test_every_spec_is_keyed_by_its_own_factor(self):
        for factor, spec in FACTOR_REGISTRY.items():
            assert spec.factor is factor

    def test_every_spec_declares_what_it_reads(self):
        for spec in FACTOR_REGISTRY.values():
            assert spec.requires, f"{spec.factor.name} declares no required fields"

    def test_required_fields_exist_on_constituent(self):
        """A typo here would make a factor permanently unusable and never say so."""
        blank = _constituent("X")
        for spec in FACTOR_REGISTRY.values():
            for field in spec.requires:
                assert hasattr(blank, field), f"{spec.factor.name} requires missing {field}"


class TestResolution:
    def test_resolves_a_supported_factor(self):
        c = _constituent("A", market_cap=1_000.0)
        assert resolve_factor(c, Factor.MARKET_CAP) == 1_000.0

    def test_unsupported_factor_raises_rather_than_scoring_zero(self):
        c = _constituent("A", market_cap=1_000.0)
        with pytest.raises(UnsupportedFactorError, match="REVENUE_GROWTH"):
            resolve_factor(c, Factor.REVENUE_GROWTH)

    def test_the_error_names_what_is_supported(self):
        with pytest.raises(UnsupportedFactorError, match="MARKET_CAP"):
            resolve_factor(_constituent("A"), Factor.MOMENTUM)

    def test_missing_data_is_none_not_an_error(self):
        """Absent data for one company differs from an unsupported factor."""
        assert resolve_factor(_constituent("A"), Factor.PRICE_TO_EARNINGS) is None

    def test_non_positive_values_count_as_missing(self):
        c = _constituent("A", pe_ratio=-12.0)
        assert resolve_factor(c, Factor.PRICE_TO_EARNINGS) is None

    def test_is_supported_agrees_with_the_registry(self):
        assert is_supported(Factor.MARKET_CAP)
        assert not is_supported(Factor.QUALITY)


class TestRankingDirection:
    def test_market_cap_ranks_largest_first(self):
        small = _constituent("SMALL", market_cap=1.0, price=1.0)
        large = _constituent("LARGE", market_cap=100.0, price=1.0)
        criteria = SelectionCriteria.builder().ranking_by(Factor.MARKET_CAP).select_top(2).build()

        assert [c.ticker for c in criteria.select([small, large])] == ["LARGE", "SMALL"]

    def test_price_to_earnings_ranks_cheapest_first(self):
        """Ranking descending on P/E selected the most expensive names."""
        cheap = _constituent("CHEAP", market_cap=10.0, price=1.0, pe_ratio=5.0)
        pricey = _constituent("PRICEY", market_cap=10.0, price=1.0, pe_ratio=90.0)
        criteria = (
            SelectionCriteria.builder().ranking_by(Factor.PRICE_TO_EARNINGS).select_top(2).build()
        )

        assert [c.ticker for c in criteria.select([pricey, cheap])] == ["CHEAP", "PRICEY"]

    def test_missing_data_sorts_last_on_a_cheapest_first_screen(self):
        """Otherwise unpriced companies win every value screen."""
        cheap = _constituent("CHEAP", market_cap=10.0, price=1.0, pe_ratio=5.0)
        unknown = _constituent("UNKNOWN", market_cap=10.0, price=1.0)
        criteria = (
            SelectionCriteria.builder().ranking_by(Factor.PRICE_TO_EARNINGS).select_top(2).build()
        )

        assert [c.ticker for c in criteria.select([unknown, cheap])] == ["CHEAP", "UNKNOWN"]

    def test_missing_data_sorts_last_on_a_largest_first_screen(self):
        big = _constituent("BIG", market_cap=100.0, price=1.0)
        unknown = _constituent("UNKNOWN", price=1.0)
        criteria = SelectionCriteria.builder().ranking_by(Factor.MARKET_CAP).select_top(2).build()

        assert [c.ticker for c in criteria.select([unknown, big])] == ["BIG", "UNKNOWN"]

    def test_ranking_on_an_unsupported_factor_raises(self):
        c = _constituent("A", market_cap=10.0, price=1.0)
        criteria = SelectionCriteria.builder().ranking_by(Factor.ROE).select_top(1).build()

        with pytest.raises(UnsupportedFactorError):
            criteria.select([c])


class TestConnectorCoverage:
    def test_yahoo_supports_every_registered_factor(self):
        for factor in SUPPORTED_FACTORS:
            assert missing_requirements(factor, YahooFinanceConnector.PROVIDES) == ()

    def test_openbb_cannot_serve_price_to_book(self):
        """OpenBB is the default source and does not populate pb_ratio."""
        assert missing_requirements(Factor.PRICE_TO_BOOK, OpenBBConnector.PROVIDES) == ("pb_ratio",)

    def test_openbb_can_serve_market_cap(self):
        assert missing_requirements(Factor.MARKET_CAP, OpenBBConnector.PROVIDES) == ()

    def test_coverage_of_an_unsupported_factor_raises(self):
        with pytest.raises(UnsupportedFactorError):
            missing_requirements(Factor.MOMENTUM, YahooFinanceConnector.PROVIDES)
