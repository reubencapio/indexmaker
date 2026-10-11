"""
Daily recalculation of live indices.

An index that is only repriced when its owner clicks a button goes stale the
moment they stop looking, and a public page showing last month's level is worse
than no page. This reprices indices after each market close and records a
snapshot, which is what builds a track record over time.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.plans import FEATURE_AUTO_REFRESH, PLANS
from app.models.embed import EmbedWidget, PublicShare
from app.models.index import Index, IndexStatus
from app.models.user import User
from app.services import delivery_service
from app.services.index_service import IndexService
from app.services.schedule import latest_market_close

logger = logging.getLogger(__name__)

# Repricing fetches a quote per constituent, so one run is bounded. The scheduler
# ticks hourly and each run takes the next batch, so a backlog clears over a few
# ticks instead of one run holding the worker for an hour.
BATCH_SIZE = 20


def _stale_index_ids(close: datetime, limit: int):
    paid_tiers = [tier for tier, plan in PLANS.items() if plan.has(FEATURE_AUTO_REFRESH)]
    shared = exists().where(
        PublicShare.index_id == Index.id,
        PublicShare.is_active == True,  # noqa: E712
    )
    embedded = exists().where(
        EmbedWidget.index_id == Index.id,
        EmbedWidget.is_active == True,  # noqa: E712
    )
    return (
        select(Index.id)
        .join(User, User.id == Index.owner_id)
        .where(Index.status == IndexStatus.ACTIVE.value)
        .where(or_(Index.last_calculated.is_(None), Index.last_calculated < close))
        # Anything the public can see is kept current on every plan; private
        # indices are refreshed for plans that include it.
        .where(or_(User.tier.in_(paid_tiers), shared, embedded))
        # Random, not oldest-first: an index that fails every time would otherwise
        # sit at the head of the queue and starve the rest.
        .order_by(func.random())
        .limit(limit)
    )


async def refresh_stale_indices(
    db: AsyncSession, now: datetime, limit: int = BATCH_SIZE
) -> dict[str, Any]:
    """Reprice indices not calculated since the last market close."""
    close = latest_market_close(now)
    ids = [row[0] for row in (await db.execute(_stale_index_ids(close, limit))).all()]

    refreshed, failed = 0, 0
    for index_id in ids:
        try:
            result = await db.execute(
                select(Index)
                .where(Index.id == index_id)
                .options(selectinload(Index.components), selectinload(Index.snapshots))
                .execution_options(populate_existing=True)
            )
            index = result.scalar_one_or_none()
            if index is None or not any(c.is_active for c in index.components):
                continue

            service = IndexService(db)
            await service.calculate_index(index)
            # One snapshot per close: a second run on the same day (a retry, a
            # manual trigger) must not add a duplicate point to the history.
            latest = index.snapshots[0].date if index.snapshots else None
            if latest is None or latest < close:
                await service.create_snapshot(index)
            await db.commit()
            refreshed += 1
        except Exception:
            logger.exception("Could not refresh index %s", index_id)
            await db.rollback()
            failed += 1
            continue

        await delivery_service.dispatch_index_event(db, index, delivery_service.EVENT_INDEX_UPDATE)

    if ids:
        logger.info("Index refresh: %d refreshed, %d failed", refreshed, failed)
    return {"candidates": len(ids), "refreshed": refreshed, "failed": failed}
