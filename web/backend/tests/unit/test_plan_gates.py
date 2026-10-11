"""Plan limits and paid features as enforced at the API."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.index import Index, IndexComponent
from app.models.user import User
from app.services import analytics_service
from app.services.market_data_service import MarketDataService


async def make_index(db: AsyncSession, owner: User, identifier: str = "GATE1") -> Index:
    index = Index(
        owner_id=owner.id,
        name=f"Index {identifier}",
        identifier=identifier,
        base_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        base_value=1000.0,
        divisor=1.0,
        current_value=1000.0,
        weighting_method="equal_weight",
    )
    db.add(index)
    await db.flush()
    # Drifted from equal weight: A has run up, B has fallen.
    db.add_all(
        [
            IndexComponent(
                index_id=index.id,
                ticker="AAA",
                name="A Corp",
                sector="Tech",
                price=60.0,
                shares=10.0,
                weight=0.6,
            ),
            IndexComponent(
                index_id=index.id,
                ticker="BBB",
                name="B Corp",
                sector="Energy",
                price=40.0,
                shares=10.0,
                weight=0.4,
            ),
        ]
    )
    await db.commit()
    return index


def fake_history(days: int = 300) -> dict[str, list[dict[str, Any]]]:
    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=days - i) for i in range(days + 1)]

    def rows(start: float, step: float) -> list[dict[str, Any]]:
        return [{"date": d.isoformat(), "close": start + step * i} for i, d in enumerate(dates)]

    return {"AAA": rows(30.0, 0.1), "BBB": rows(40.0, 0.0), "SPY": rows(400.0, 0.2)}


@pytest.fixture
def priced(monkeypatch: pytest.MonkeyPatch) -> None:
    async def history(self: MarketDataService, tickers, start, end):
        data = fake_history()
        return {t: data[t] for t in tickers if t in data}

    monkeypatch.setattr(MarketDataService, "get_prices_for_tickers", history)
    analytics_service._cache.clear()


class TestIndexLimit:
    async def test_free_plan_stops_at_three_indices(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        for i in range(3):
            await make_index(db_session, test_user, f"LIM{i}")
        response = await client.post(
            "/api/v1/indices",
            headers=auth_headers,
            json={
                "name": "One too many",
                "identifier": "LIM9",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 402
        assert response.json()["detail"]["code"] == "upgrade_required"

    async def test_ai_builder_cannot_bypass_the_limit(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        for i in range(3):
            await make_index(db_session, test_user, f"AIL{i}")
        response = await client.post(
            "/api/v1/ai/create", headers=auth_headers, json={"description": "top tech stocks"}
        )
        assert response.status_code == 402


class TestPaidFeatures:
    async def test_delivery_requires_pro(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/delivery/webhooks",
            headers=auth_headers,
            json={"name": "hook", "url": "https://example.com/hook"},
        )
        assert response.status_code == 402
        assert response.json()["detail"]["feature"] == "delivery"

    async def test_export_requires_pro_then_returns_csv(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        index = await make_index(db_session, test_user)
        url = f"/api/v1/indices/{index.id}/export"
        assert (await client.get(url, headers=auth_headers)).status_code == 402

        test_user.tier = "pro"
        await db_session.commit()
        response = await client.get(url, headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        lines = response.text.strip().splitlines()
        assert lines[0].startswith("Ticker,Name,Sector")
        assert lines[1].startswith("AAA,A Corp,Tech")

    async def test_second_share_link_requires_pro(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        index = await make_index(db_session, test_user)
        first = await client.post(
            "/api/v1/embeds/shares", headers=auth_headers, json={"index_id": index.id}
        )
        assert first.status_code == 201
        # Links must open the web app, not the API host.
        assert "/public/" in first.json()["public_url"]
        second = await client.post(
            "/api/v1/embeds/shares", headers=auth_headers, json={"index_id": index.id}
        )
        assert second.status_code == 402

    async def test_unbranded_widget_requires_pro(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        index = await make_index(db_session, test_user)
        response = await client.post(
            "/api/v1/embeds/widgets",
            headers=auth_headers,
            json={"index_id": index.id, "name": "w", "hide_branding": True},
        )
        assert response.status_code == 402


class TestAnalytics:
    async def test_analytics_are_computed_from_price_history(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, test_user)
        response = await client.get(
            f"/api/v1/indices/{index.id}/analytics?period=6M", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["methodology"] == "current_composition"
        assert data["benchmark"] == "SPY"
        # The chart is anchored to the published level.
        assert data["series"][-1]["value"] == pytest.approx(1000.0)
        # AAA rose steadily and BBB was flat, so the index rose with no drawdown.
        assert data["stats"]["total_return"] > 0
        assert data["stats"]["max_drawdown"] == pytest.approx(0.0)
        assert data["stats"]["beta"] is not None
        assert {s["name"] for s in data["sector_allocation"]} == {"Tech", "Energy"}
        assert data["concentration"]["count"] == 2

    async def test_same_request_returns_identical_numbers(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, test_user)
        url = f"/api/v1/indices/{index.id}/analytics?period=3M"
        first = (await client.get(url, headers=auth_headers)).json()
        second = (await client.get(url, headers=auth_headers)).json()
        assert first["stats"] == second["stats"]

    async def test_long_history_requires_pro(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, test_user)
        response = await client.get(
            f"/api/v1/indices/{index.id}/analytics?period=5Y", headers=auth_headers
        )
        assert response.status_code == 402

    async def test_no_price_history_is_a_clear_409(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        analytics_service._cache.clear()
        index = await make_index(db_session, test_user)
        response = await client.get(f"/api/v1/indices/{index.id}/analytics", headers=auth_headers)
        assert response.status_code == 409

    async def test_other_users_index_is_forbidden(
        self, client: AsyncClient, admin_auth_headers, test_user: User, db_session: AsyncSession
    ):
        index = await make_index(db_session, test_user)
        response = await client.get(
            f"/api/v1/indices/{index.id}/analytics", headers=admin_auth_headers
        )
        assert response.status_code == 403


class TestRebalance:
    async def test_preview_reports_real_drift_against_targets(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        index = await make_index(db_session, test_user)
        response = await client.get(
            f"/api/v1/indices/{index.id}/rebalance/preview", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        by_ticker = {c["ticker"]: c for c in data["components"]}
        assert by_ticker["AAA"]["target_weight"] == pytest.approx(0.5)
        assert by_ticker["AAA"]["drift"] == pytest.approx(0.1)
        assert by_ticker["BBB"]["drift"] == pytest.approx(-0.1)
        assert data["turnover"] == pytest.approx(0.1)
        assert data["last_rebalance"] is None

    async def test_rebalance_resets_weights_without_moving_the_level(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        index = await make_index(db_session, test_user)
        response = await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["current_value"] == pytest.approx(1000.0)

        preview = (
            await client.get(f"/api/v1/indices/{index.id}/rebalance/preview", headers=auth_headers)
        ).json()
        assert preview["turnover"] == pytest.approx(0.0, abs=1e-9)
        assert preview["last_rebalance"] is not None


class TestPublicShare:
    async def test_share_link_serves_the_index_without_auth(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, test_user)
        created = await client.post(
            "/api/v1/embeds/shares",
            headers=auth_headers,
            json={"index_id": index.id, "slug": "my-index"},
        )
        assert created.status_code == 201

        response = await client.get("/api/v1/embeds/public/shares/my-index")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == index.name
        assert len(data["components"]) == 2
        assert data["series"] and data["stats"]["total_return"] is not None
        assert data["show_branding"] is True
        # Nothing about the owner leaks into a public payload.
        assert "owner_id" not in data

    async def test_password_protected_share(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession
    ):
        index = await make_index(db_session, test_user)
        await client.post(
            "/api/v1/embeds/shares",
            headers=auth_headers,
            json={"index_id": index.id, "slug": "locked", "password": "hunter22"},
        )
        url = "/api/v1/embeds/public/shares/locked"
        assert (await client.get(url)).json()["detail"]["code"] == "password_required"
        assert (await client.get(url, params={"password": "nope"})).status_code == 401
        assert (await client.get(url, params={"password": "hunter22"})).status_code == 200

    async def test_unknown_slug_is_404(self, client: AsyncClient):
        assert (await client.get("/api/v1/embeds/public/shares/nope")).status_code == 404

    async def test_widget_view_by_token(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, test_user)
        widget = (
            await client.post(
                "/api/v1/embeds/widgets",
                headers=auth_headers,
                json={"index_id": index.id, "name": "chart"},
            )
        ).json()
        assert "/embed/" in widget["embed_code"]
        response = await client.get(f"/api/v1/embeds/public/widgets/{widget['embed_token']}")
        assert response.status_code == 200
        assert response.json()["series"]
        assert response.json()["components"] is None


class TestAccount:
    async def test_password_change_requires_the_current_password(
        self, client: AsyncClient, auth_headers
    ):
        url = "/api/v1/users/me"
        missing = await client.patch(url, headers=auth_headers, json={"password": "newpassword1"})
        assert missing.status_code == 400
        wrong = await client.patch(
            url, headers=auth_headers, json={"password": "newpassword1", "current_password": "x"}
        )
        assert wrong.status_code == 400
        ok = await client.patch(
            url,
            headers=auth_headers,
            json={"password": "newpassword1", "current_password": "testpassword"},
        )
        assert ok.status_code == 200
        login = await client.post(
            "/api/v1/auth/login", json={"email": "test@example.com", "password": "newpassword1"}
        )
        assert login.status_code == 200

    async def test_login_is_case_insensitive_on_email(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login", json={"email": "Test@Example.com", "password": "testpassword"}
        )
        assert response.status_code == 200

    async def test_register_rejects_same_address_in_different_case(
        self, client: AsyncClient, test_user: User
    ):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "TEST@example.com", "password": "anotherpassword"},
        )
        assert response.status_code == 400
