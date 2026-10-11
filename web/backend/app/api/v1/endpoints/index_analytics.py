"""
Index analytics, rebalancing and export endpoints.

Mounted under /indices alongside the CRUD routes.
"""

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.core.plans import (
    FEATURE_DATA_EXPORT,
    FEATURE_EXTENDED_HISTORY,
    get_plan,
    require_feature,
    upgrade_required,
)
from app.models.index import Index, IndexSnapshot
from app.services import analytics_service, delivery_service, follower_service
from app.services.analytics_service import PERIOD_YEARS, AnalyticsUnavailableError
from app.services.index_service import IndexService

logger = logging.getLogger(__name__)

router = APIRouter()


async def _owned_index(db: DBSession, user_id: str, index_id: str) -> Index:
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()
    if not index:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
    if index.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return index


def _csv_response(rows: list[list[Any]], filename: str) -> Response:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _check_period(tier: str, period: str) -> None:
    if period not in PERIOD_YEARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown period. Choose one of: {', '.join(PERIOD_YEARS)}",
        )
    plan = get_plan(tier)
    if PERIOD_YEARS[period] > plan.analytics_history_years:
        raise upgrade_required(
            f"Your {plan.name} plan includes {plan.analytics_history_years} year of analytics "
            "history. Upgrade to Pro for up to 10 years.",
            feature=FEATURE_EXTENDED_HISTORY,
        )


@router.get("/{index_id}/analytics")
async def get_index_analytics(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    period: str = Query(default="1Y"),
    benchmark: str = Query(default=analytics_service.DEFAULT_BENCHMARK, max_length=12),
) -> dict[str, Any]:
    """
    Performance and risk analytics computed from real constituent prices.

    The series values today's holdings across the period (see
    `analytics_service`); the response's `methodology` field says so.
    """
    index = await _owned_index(db, current_user.id, index_id)
    _check_period(current_user.tier, period)

    try:
        return await analytics_service.compute_index_analytics(
            index, period, benchmark.upper().strip() or analytics_service.DEFAULT_BENCHMARK
        )
    except AnalyticsUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{index_id}/analytics/export")
async def export_index_history(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    period: str = Query(default="1Y"),
    benchmark: str = Query(default=analytics_service.DEFAULT_BENCHMARK, max_length=12),
) -> Response:
    """Download the index level history as CSV."""
    require_feature(current_user.tier, FEATURE_DATA_EXPORT)
    index = await _owned_index(db, current_user.id, index_id)
    _check_period(current_user.tier, period)

    try:
        data = await analytics_service.compute_index_analytics(
            index, period, benchmark.upper().strip() or analytics_service.DEFAULT_BENCHMARK
        )
    except AnalyticsUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    bench_header = f"{data['benchmark']} (rebased)" if data["benchmark"] else "Benchmark"
    rows: list[list[Any]] = [["Date", index.identifier, bench_header, "Drawdown"]]
    rows += [[p["date"], p["value"], p["benchmark"] or "", p["drawdown"]] for p in data["series"]]
    return _csv_response(rows, f"{index.identifier}_history_{period}.csv")


@router.get("/{index_id}/export")
async def export_constituents(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
) -> Response:
    """Download current constituents and weights as CSV."""
    require_feature(current_user.tier, FEATURE_DATA_EXPORT)
    index = await _owned_index(db, current_user.id, index_id)

    rows: list[list[Any]] = [
        ["Ticker", "Name", "Sector", "Country", "Weight", "Price", "Shares", "Market Cap"]
    ]
    for c in index.components:
        if c.is_active:
            rows.append(
                [
                    c.ticker,
                    c.name or "",
                    c.sector or "",
                    c.country or "",
                    round(c.weight, 8),
                    c.price if c.price is not None else "",
                    c.shares,
                    c.market_cap if c.market_cap is not None else "",
                ]
            )
    return _csv_response(rows, f"{index.identifier}_constituents.csv")


async def _last_rebalance(db: DBSession, index_id: str) -> datetime | None:
    return await db.scalar(
        select(IndexSnapshot.date)
        .where(IndexSnapshot.index_id == index_id)
        .where(IndexSnapshot.is_rebalance_day == True)  # noqa: E712
        .order_by(IndexSnapshot.date.desc())
        .limit(1)
    )


@router.get("/{index_id}/rebalance/preview")
async def preview_rebalance(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
) -> dict[str, Any]:
    """
    Current weights against the methodology's targets.

    Current weights are what the holdings are worth at the last calculation;
    targets are what a rebalance would reset them to. The difference is real
    drift, driven by price moves since the last rebalance.
    """
    index = await _owned_index(db, current_user.id, index_id)
    targets = IndexService(db)._target_weights(index)

    rows = []
    for c in index.components:
        if not c.is_active:
            continue
        target = targets.get(c.ticker, 0.0)
        rows.append(
            {
                "ticker": c.ticker,
                "name": c.name,
                "price": c.price,
                "current_weight": c.weight or 0.0,
                "target_weight": target,
                "drift": (c.weight or 0.0) - target,
                # Unpriced names cannot be valued, so a rebalance drops them.
                "priced": bool(c.price and c.price > 0),
            }
        )
    rows.sort(key=lambda r: -abs(r["drift"]))

    return {
        "index_id": index.id,
        "initialised": bool(index.divisor and index.divisor > 0),
        "last_calculated": index.last_calculated,
        "last_rebalance": await _last_rebalance(db, index.id),
        "rebalance_frequency": index.rebalance_frequency,
        # One-way turnover: the fraction of the portfolio that changes hands.
        "turnover": sum(abs(r["drift"]) for r in rows) / 2,
        "max_drift": max((abs(r["drift"]) for r in rows), default=0.0),
        "components": rows,
    }


@router.post("/{index_id}/rebalance")
async def rebalance_index(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Rebalance to target weights at current prices.

    The index level is unchanged by construction: the divisor is reset so that
    reallocating the portfolio produces no return of its own.
    """
    result = await db.execute(
        select(Index)
        .where(Index.id == index_id)
        .options(selectinload(Index.components), selectinload(Index.snapshots))
    )
    index = result.scalar_one_or_none()
    if not index:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
    if index.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not any(c.is_active for c in index.components):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This index has no constituents to rebalance.",
        )

    previous_weights = {c.ticker: c.weight or 0 for c in index.components if c.is_active}

    await IndexService(db).rebalance_index(index)
    await db.commit()
    await delivery_service.dispatch_index_event(db, index, delivery_service.EVENT_REBALANCE)

    # Followers are told after the response is sent: SMTP is slow, and a mail
    # problem must not turn a successful rebalance into an error.
    try:
        notifications = await follower_service.rebalance_notifications(db, index, previous_weights)
    except Exception:
        logger.exception("Could not prepare follower notifications for index %s", index.id)
        notifications = []
    if notifications:
        background_tasks.add_task(follower_service.send_all, notifications)

    return {
        "index_id": index.id,
        "current_value": index.current_value,
        "rebalanced_at": datetime.now(timezone.utc),
    }
