"""
Unit tests for capability reporting.

The point of this endpoint is that a factor which cannot be computed is reported
as unavailable with a reason, rather than being offered and then silently scoring
every constituent the same.
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import capabilities


class _Connector:
    """Stands in for a data source with a declared coverage set."""

    def __init__(self, name: str, provides: frozenset[str]) -> None:
        self._name = name
        self.PROVIDES = provides

    def get_name(self) -> str:
        return self._name


class TestSupportedFactorsEndpoint:
    def test_lists_only_registered_factors(self):
        app = FastAPI()
        app.include_router(capabilities.router, prefix="/capabilities")
        response = TestClient(app).get("/capabilities/factors")

        assert response.status_code == 200
        names = response.json()
        assert "MARKET_CAP" in names
        # Named by the enum but with no resolver behind it.
        assert "REVENUE_GROWTH" not in names
        assert "MOMENTUM" not in names


class TestCapabilitiesReport:
    def _get(self, connector: _Connector):
        app = FastAPI()
        app.include_router(capabilities.router, prefix="/capabilities")
        dependency = capabilities.CurrentUser.__metadata__[0].dependency
        app.dependency_overrides[dependency] = lambda: MagicMock(id="user-1")
        with patch.object(capabilities, "get_user_connector", return_value=connector):
            return TestClient(app).get("/capabilities")

    def test_reports_the_active_data_source(self):
        response = self._get(_Connector("Yahoo Finance", frozenset({"market_cap"})))
        assert response.json()["data_source"] == "Yahoo Finance"

    def test_factor_with_its_field_present_is_available(self):
        response = self._get(_Connector("Yahoo Finance", frozenset({"market_cap"})))
        by_name = {f["factor"]: f for f in response.json()["factors"]}
        assert by_name["MARKET_CAP"]["available"] is True

    def test_factor_missing_its_field_is_unavailable_with_a_reason(self):
        """The OpenBB case: implemented, but the source does not supply pb_ratio."""
        response = self._get(_Connector("OpenBB", frozenset({"market_cap"})))
        by_name = {f["factor"]: f for f in response.json()["factors"]}

        assert by_name["PRICE_TO_BOOK"]["available"] is False
        assert by_name["PRICE_TO_BOOK"]["missing_fields"] == ["pb_ratio"]
        assert "OpenBB" in by_name["PRICE_TO_BOOK"]["reason"]

    def test_unimplemented_factors_are_listed_not_omitted(self):
        """Users should see why a factor is missing, not have it silently absent."""
        response = self._get(_Connector("Yahoo Finance", frozenset({"market_cap"})))
        by_name = {f["factor"]: f for f in response.json()["factors"]}

        assert by_name["REVENUE_GROWTH"]["available"] is False
        assert by_name["REVENUE_GROWTH"]["reason"] == "Not yet implemented"

    def test_valuation_ratios_report_their_direction(self):
        response = self._get(_Connector("Yahoo", frozenset({"pe_ratio"})))
        by_name = {f["factor"]: f for f in response.json()["factors"]}
        assert by_name["PRICE_TO_EARNINGS"]["higher_is_better"] is False
        assert by_name["MARKET_CAP"]["higher_is_better"] is True

    def test_a_connector_without_declared_coverage_blocks_everything(self):
        """Failing closed beats offering factors that quietly do nothing."""
        response = self._get(_Connector("Mystery", frozenset()))
        assert all(f["available"] is False for f in response.json()["factors"])
