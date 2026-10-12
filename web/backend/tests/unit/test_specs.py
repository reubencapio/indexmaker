"""
Tests for spec-driven index builds.

The property under test throughout: an index's members come from its spec and
the market data, through the indexforge library -- never from a list the AI
recalled -- so the same spec and data always give the same index.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from httpx import AsyncClient
from indexforge import SnapshotConnector, SpecError, build
from indexforge.core.constituent import Constituent
from indexforge.core.types import Currency
from indexforge.data.connectors.base import DataConnector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.index import Index, IndexStatus
from app.models.user import User
from app.services import spec_service
from app.services.spec_service import (
    BuildError,
    apply_build,
    run_build,
    spec_from_config,
    stored_snapshot,
)


class FakeMarket(DataConnector):
    """A fixed market that can be screened."""

    def __init__(self, constituents, can_screen=True):
        self._constituents = constituents
        self._can_screen = can_screen

    def get_prices(self, tickers, start_date, end_date):  # pragma: no cover - unused
        raise NotImplementedError

    def get_constituent_data(self, tickers, as_of_date=None):
        return [
            Constituent.from_dict(c.to_dict()) for c in self._constituents if c.ticker in tickers
        ]

    def get_market_cap(self, tickers, as_of_date=None):  # pragma: no cover - unused
        return {}

    def get_fx_rate(self, base, quote, as_of_date=None):
        return 1.0 if base == quote else {"SEK/EUR": 0.09}.get(f"{base}/{quote}")

    def screen(self, countries, sectors=None, min_market_cap=None, currency="USD"):
        if not self._can_screen:
            return super().screen(countries, sectors, min_market_cap, currency)
        return sorted(c.ticker for c in self._constituents)

    def get_name(self):
        return "Fake Market"


def company(ticker, cap, country="Germany", sector="Technology", currency=Currency.EUR, **kw):
    return Constituent(
        ticker=ticker,
        name=f"{ticker} AG",
        market_cap=cap,
        free_float_market_cap=cap,
        currency=currency,
        country=country,
        sector=sector,
        price=10.0,
        business_description=kw.pop("description", "Makes things"),
        **kw,
    )


MARKET = [
    company("BIG.DE", 300e9),
    company("MID.DE", 50e9),
    company("LOW.DE", 5e9),
    company("TEL.DE", 100e9, sector="Communication Services"),
    company("ERIC.ST", 900e9, country="Sweden", currency=Currency.SEK),
    company("US.DE", 4000e9, country="United States"),
]

CONFIG = {
    "name": "German Tech",
    "identifier": "DETECH",
    "description": "Large German technology companies",
    "currency": "EUR",
    "base_date": "2025-01-01",
    "base_value": 1000,
    "countries": ["DE", "SE"],
    "sectors": ["TECHNOLOGY"],
    "tickers": [],
    "theme_keywords": [],
    "min_market_cap": 1_000_000_000,
    "max_components": 3,
    "weighting_method": "equal_weight",
    "max_weight": 0.10,
    "rebalance_frequency": "quarterly",
    "custom_rules": {"min_dividend_yield": None},
}


@pytest.fixture
def market(monkeypatch):
    fake = FakeMarket(MARKET)
    monkeypatch.setattr(spec_service, "connector_for", lambda source: fake)
    return fake


class TestSpecFromConfig:
    def test_rules_without_named_companies_become_a_screen(self):
        spec = spec_from_config(CONFIG)
        assert spec["universe"] == {
            "screen": True,
            "countries": ["Germany", "Sweden"],
            "sectors": ["Technology"],
            "min_market_cap": 1_000_000_000.0,
        }
        assert spec["selection"] == {"rank_by": "MARKET_CAP", "top": 3}

    def test_named_companies_are_the_whole_universe(self):
        spec = spec_from_config({**CONFIG, "tickers": ["aapl", "MSFT", "AAPL"]})
        # Country and sector rules are not applied to companies the user named.
        assert spec["universe"] == {"tickers": ["AAPL", "MSFT"]}

    def test_a_request_with_no_place_or_size_is_still_bounded(self):
        spec = spec_from_config({**CONFIG, "countries": [], "min_market_cap": None})
        assert spec["universe"]["countries"] == ["United States"]
        assert spec["universe"]["min_market_cap"] == 1_000_000_000.0

    def test_unrecognised_countries_and_sectors_are_dropped(self):
        spec = spec_from_config({**CONFIG, "countries": ["DE", "ZZ"], "sectors": ["WIZARDRY"]})
        assert spec["universe"]["countries"] == ["Germany"]
        assert "sectors" not in spec["universe"]

    def test_theme_keywords_apply_to_a_screen_only(self):
        themed = {**CONFIG, "theme_keywords": ["quantum"]}
        assert spec_from_config(themed)["selection"]["theme_keywords"] == ["quantum"]
        named = spec_from_config({**themed, "tickers": ["AAPL"]})
        assert "theme_keywords" not in named["selection"]

    def test_weight_cap_is_kept_only_where_it_does_something(self):
        assert "max_weight" not in spec_from_config(CONFIG)["weighting"]
        capped = spec_from_config({**CONFIG, "weighting_method": "market_cap"})
        assert capped["weighting"] == {"method": "market_cap", "max_weight": 0.10}

    def test_an_impossible_configuration_is_a_spec_error(self):
        with pytest.raises(SpecError):
            spec_from_config({**CONFIG, "weighting_method": "vibes"})


class TestRunBuild:
    def test_members_follow_the_rules_not_the_candidate_order(self, market):
        result = run_build(spec_from_config(CONFIG))

        # ERIC's 900bn kronor is 81bn euros: second, not first.
        assert [c.ticker for c in result.constituents] == ["BIG.DE", "ERIC.ST", "MID.DE"]
        assert result.exclusions == {
            "LOW.DE": "ranked outside the selection",
            "TEL.DE": "sector Communication Services is not in the universe",
            "US.DE": "country United States is not in the universe",
        }

    def test_the_same_spec_and_data_always_give_the_same_index(self, market):
        spec = spec_from_config(CONFIG)
        first = run_build(spec).to_dict()
        assert all(run_build(spec).to_dict() == first for _ in range(3))

    def test_a_country_the_source_cannot_search_does_not_fail_the_build(self, market):
        # "EU" includes Luxembourg, which Yahoo has no exchange for.
        market.unscreenable_countries = lambda countries: [
            c for c in countries if c == "Luxembourg"
        ]
        spec = spec_from_config({**CONFIG, "countries": ["DE", "SE", "LU"]})

        result = run_build(spec)

        assert [c.ticker for c in result.constituents] == ["BIG.DE", "ERIC.ST", "MID.DE"]
        assert result.unscreened == ["Luxembourg"]

    def test_no_members_is_an_error_with_advice(self, market):
        spec = spec_from_config({**CONFIG, "min_market_cap": 10e15})
        with pytest.raises(BuildError, match="No company met the rules"):
            run_build(spec)

    def test_a_source_that_cannot_screen_points_to_one_that_can(self, monkeypatch):
        fake = FakeMarket(MARKET, can_screen=False)
        monkeypatch.setattr(spec_service, "connector_for", lambda source: fake)
        with pytest.raises(BuildError, match="Switch to Yahoo Finance"):
            run_build(spec_from_config(CONFIG))

    def test_a_rate_limited_source_fails_the_build_with_its_own_advice(self, market, monkeypatch):
        from indexforge import DataSourceError

        def refuse(tickers, as_of_date=None):
            raise DataSourceError("Yahoo Finance is limiting requests. Wait a few minutes.")

        monkeypatch.setattr(market, "get_constituent_data", refuse)
        with pytest.raises(BuildError, match="Wait a few minutes"):
            run_build(spec_from_config(CONFIG))

    def test_stored_snapshot_replays_to_the_same_index(self, market):
        spec = spec_from_config(CONFIG)
        result = run_build(spec)

        snapshot = stored_snapshot(spec, result)
        assert all(row["business_description"] == "" for row in snapshot["constituents"])

        replayed = build(spec, as_of=result.as_of, connector=SnapshotConnector(snapshot))
        assert replayed.to_dict()["constituents"] == result.to_dict()["constituents"]

    def test_descriptions_are_kept_when_a_theme_filter_reads_them(self, market):
        spec = spec_from_config({**CONFIG, "theme_keywords": ["things"]})
        snapshot = stored_snapshot(spec, run_build(spec))
        assert any(row["business_description"] for row in snapshot["constituents"])


async def _make_index(db: AsyncSession, user: User, **fields) -> Index:
    index = Index(
        owner_id=user.id,
        name="German Tech",
        identifier=fields.pop("identifier", "DETECH"),
        currency="USD",
        base_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        base_value=1000.0,
        status=fields.pop("status", IndexStatus.BUILDING.value),
        **fields,
    )
    db.add(index)
    await db.commit()
    return index


class TestApplyBuild:
    @pytest.mark.asyncio
    async def test_index_takes_its_rules_members_and_evidence_from_the_build(
        self, db_session: AsyncSession, test_user: User, market
    ):
        index = await _make_index(db_session, test_user)
        spec = spec_from_config(CONFIG)
        result = run_build(spec)

        count = await db_session.run_sync(lambda s: apply_build(s, index, spec, result))
        await db_session.commit()

        loaded = (
            await db_session.execute(
                select(Index)
                .where(Index.id == index.id)
                .options(selectinload(Index.components))
                .execution_options(populate_existing=True)
            )
        ).scalar_one()

        assert count == 3
        assert loaded.currency == "EUR"
        assert loaded.spec == spec
        assert loaded.build_info["data_source"] == "Fake Market"
        assert loaded.build_info["candidates"] == 6
        assert loaded.build_info["unscreened"] == []
        assert loaded.build_info["exclusions"]["US.DE"].startswith("country United States")
        by_ticker = {c.ticker: c for c in loaded.components}
        assert set(by_ticker) == {"BIG.DE", "ERIC.ST", "MID.DE"}
        # Stored in the index currency, not the stock's trading currency.
        assert by_ticker["ERIC.ST"].market_cap == pytest.approx(81e9)
        assert sum(c.weight for c in loaded.components) == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_a_rebuild_replaces_the_previous_members(
        self, db_session: AsyncSession, test_user: User, market
    ):
        index = await _make_index(db_session, test_user)
        spec = spec_from_config(CONFIG)
        await db_session.run_sync(lambda s: apply_build(s, index, spec, run_build(spec)))
        await db_session.commit()

        smaller = spec_from_config({**CONFIG, "max_components": 1})
        await db_session.run_sync(lambda s: apply_build(s, index, smaller, run_build(smaller)))
        await db_session.commit()

        loaded = (
            await db_session.execute(
                select(Index)
                .where(Index.id == index.id)
                .options(selectinload(Index.components))
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert [c.ticker for c in loaded.components] == ["BIG.DE"]


class TestSpecEndpoints:
    @pytest.mark.asyncio
    async def test_create_from_spec_stores_it_and_queues_the_build(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        spec = spec_from_config(CONFIG)
        with patch("app.tasks.build_index_from_spec_task") as task:
            response = await client.post(
                "/api/v1/indices/from-spec", headers=auth_headers, json=spec
            )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "building"
        assert data["spec"] == spec
        assert data["identifier"] == "DETECH"
        task.delay.assert_called_once()
        assert task.delay.call_args.kwargs["index_id"] == data["id"]

    @pytest.mark.asyncio
    async def test_invalid_spec_is_rejected_with_the_reason(
        self, client: AsyncClient, auth_headers: dict
    ):
        spec = spec_from_config(CONFIG)
        spec["universe"]["min_marketcap"] = 5
        with patch("app.tasks.build_index_from_spec_task") as task:
            response = await client.post(
                "/api/v1/indices/from-spec", headers=auth_headers, json=spec
            )
        assert response.status_code == 422
        assert "min_marketcap" in response.json()["detail"]
        task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_from_spec_respects_the_plan_limit(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        for i in range(3):
            await _make_index(db_session, test_user, identifier=f"FULL{i}")
        with patch("app.tasks.build_index_from_spec_task"):
            response = await client.post(
                "/api/v1/indices/from-spec", headers=auth_headers, json=spec_from_config(CONFIG)
            )
        assert response.status_code == 402

    @pytest.mark.asyncio
    async def test_spec_and_data_downloads_reproduce_the_index(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        market,
    ):
        index = await _make_index(db_session, test_user)
        spec = spec_from_config(CONFIG)
        result = run_build(spec)
        await db_session.run_sync(lambda s: apply_build(s, index, spec, result))
        await db_session.commit()

        spec_file = await client.get(f"/api/v1/indices/{index.id}/spec", headers=auth_headers)
        data_file = await client.get(f"/api/v1/indices/{index.id}/build-data", headers=auth_headers)

        assert spec_file.status_code == 200
        assert 'filename="detech.yaml"' in spec_file.headers["content-disposition"]
        assert data_file.status_code == 200
        assert 'filename="detech.data.json"' in data_file.headers["content-disposition"]

        # What a third party would do with the two files.
        rebuilt = build(
            yaml.safe_load(spec_file.text),
            as_of=result.as_of,
            connector=SnapshotConnector(data_file.json()),
        )
        assert rebuilt.to_dict()["constituents"] == result.to_dict()["constituents"]

    @pytest.mark.asyncio
    async def test_spec_download_as_json(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        spec = spec_from_config(CONFIG)
        index = await _make_index(db_session, test_user, spec=spec)
        response = await client.get(
            f"/api/v1/indices/{index.id}/spec?format=json", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == spec

    @pytest.mark.asyncio
    async def test_downloads_are_for_the_owner_only(
        self, client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, test_user
    ):
        index = await _make_index(db_session, test_user, spec=spec_from_config(CONFIG))
        for path in ("spec", "build-data"):
            response = await client.get(
                f"/api/v1/indices/{index.id}/{path}", headers=admin_auth_headers
            )
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_index_without_a_spec_has_nothing_to_download_or_rebuild(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        index = await _make_index(db_session, test_user)
        assert (
            await client.get(f"/api/v1/indices/{index.id}/spec", headers=auth_headers)
        ).status_code == 404
        assert (
            await client.get(f"/api/v1/indices/{index.id}/build-data", headers=auth_headers)
        ).status_code == 404
        with patch("app.tasks.build_index_from_spec_task") as task:
            response = await client.post(
                f"/api/v1/indices/{index.id}/rebuild", headers=auth_headers
            )
        assert response.status_code == 409
        task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_rebuild_queues_a_build_of_the_stored_spec(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        index = await _make_index(
            db_session, test_user, spec=spec_from_config(CONFIG), status="active"
        )
        with patch("app.tasks.build_index_from_spec_task") as task:
            response = await client.post(
                f"/api/v1/indices/{index.id}/rebuild", headers=auth_headers
            )
        assert response.status_code == 200
        assert response.json()["status"] == "building"
        task.delay.assert_called_once()


class TestDataSourceChoice:
    @pytest.mark.asyncio
    async def test_default_source_is_yahoo(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/market-data-providers/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["active_source"] == "yahoo"

    @pytest.mark.asyncio
    async def test_choice_is_saved_on_the_user(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        target = "app.api.v1.endpoints.market_data_providers._test_provider"
        with patch(target, new=AsyncMock(return_value=(True, "ok"))):
            response = await client.post(
                "/api/v1/market-data-providers/active",
                headers=auth_headers,
                json={"source_id": "openbb"},
            )
        assert response.status_code == 200

        await db_session.refresh(test_user)
        assert test_user.market_data_source == "openbb"
        listing = await client.get("/api/v1/market-data-providers/", headers=auth_headers)
        assert listing.json()["active_source"] == "openbb"

    @pytest.mark.asyncio
    async def test_a_failed_connection_does_not_change_the_choice(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        target = "app.api.v1.endpoints.market_data_providers._test_provider"
        with patch(target, new=AsyncMock(return_value=(False, "down"))):
            await client.post(
                "/api/v1/market-data-providers/active",
                headers=auth_headers,
                json={"source_id": "openbb"},
            )
        await db_session.refresh(test_user)
        assert test_user.market_data_source is None


def test_connector_for_defaults_to_yahoo():
    from indexforge.data.connectors.yahoo import YahooFinanceConnector

    assert isinstance(spec_service.connector_for(None), YahooFinanceConnector)
    assert isinstance(spec_service.connector_for("yahoo"), YahooFinanceConnector)
