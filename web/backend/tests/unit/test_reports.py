"""Factsheets: real figures, honest gaps, and files that open."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.index import Index, IndexComponent
from app.models.user import User
from app.services import analytics_service
from app.services.market_data_service import MarketDataService


async def make_index(db: AsyncSession, owner: User) -> Index:
    index = Index(
        owner_id=owner.id,
        name="Alpha <script>alert(1)</script>",
        identifier="FACTS",
        base_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        base_value=1000.0,
        divisor=1.0,
        current_value=1000.0,
    )
    db.add(index)
    await db.flush()
    db.add(
        IndexComponent(
            index_id=index.id, ticker="AAA", name="A Corp", price=100.0, shares=10.0, weight=1.0
        )
    )
    await db.commit()
    return index


@pytest.fixture
def rising_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    async def history(
        self: MarketDataService, tickers, start, end
    ) -> dict[str, list[dict[str, Any]]]:
        today = datetime.now(timezone.utc).date()
        days = [today - timedelta(days=400 - i) for i in range(401)]
        return {
            t: [{"date": d.isoformat(), "close": 50.0 + i * 0.125} for i, d in enumerate(days)]
            for t in tickers
        }

    monkeypatch.setattr(MarketDataService, "get_prices_for_tickers", history)
    analytics_service._cache.clear()


class TestFactsheet:
    async def test_metrics_come_from_price_history(
        self, client: AsyncClient, auth_headers, test_user: User, db_session, rising_prices
    ):
        index = await make_index(db_session, test_user)
        response = await client.get(
            f"/api/v1/reports/quick/{index.id}?format=json", headers=auth_headers
        )
        assert response.status_code == 200
        metrics = response.json()["metrics"]
        assert metrics["total_return"] > 0
        # A steadily rising series never draws down.
        assert metrics["max_drawdown"] == pytest.approx(0.0)
        assert metrics["as_of"] is not None

    async def test_unknown_figures_print_as_na_not_zero(
        self, client: AsyncClient, auth_headers, test_user: User, db_session
    ):
        analytics_service._cache.clear()
        index = await make_index(db_session, test_user)
        response = await client.get(f"/api/v1/reports/quick/{index.id}", headers=auth_headers)
        assert response.status_code == 200
        assert "n/a" in response.text
        assert "+0.00%" not in response.text

    async def test_index_name_is_escaped(
        self, client: AsyncClient, auth_headers, test_user: User, db_session
    ):
        analytics_service._cache.clear()
        index = await make_index(db_session, test_user)
        html = (await client.get(f"/api/v1/reports/quick/{index.id}", headers=auth_headers)).text
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    async def test_generated_report_downloads_as_html(
        self,
        client: AsyncClient,
        auth_headers,
        test_user: User,
        db_session,
        rising_prices,
        monkeypatch,
    ):
        # The generation task opens its own database session; this test is about
        # the record the endpoint creates, so the task itself is not run.
        async def skip(*args: Any, **kwargs: Any) -> None:
            return None

        monkeypatch.setattr("app.core.task_runner.run_task_async", skip)
        index = await make_index(db_session, test_user)
        created = await client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"index_id": index.id, "report_format": "pdf"},
        )
        assert created.status_code == 202, created.text
        # Whatever was asked for, the record says what was actually produced.
        assert created.json()["report_format"] == "html"
