"""
The database-backed store of company details, and the job that keeps it filled.

See `CompanyDetail` for why details are stored. Every user's builds read the
same rows, so two people building the same rules read the same details.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from indexforge import Constituent
from indexforge.data.connectors.base import DataConnector, DataSourceError
from indexforge.data.connectors.cached import DEFAULT_MAX_AGE
from indexforge.data.store import CompanyStore
from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.company import CompanyDetail

logger = logging.getLogger(__name__)

#: Rows per statement, to keep statements and their parameter lists small.
_BATCH = 500

#: Companies the scheduled job asks the source for in one request round.
_FILL_STEP = 25


def _default_sessions() -> Session:
    from app.db.session import SessionLocal

    return SessionLocal()


class DatabaseCompanyStore(CompanyStore):
    """
    Company details in the `company_details` table.

    Each call uses its own short transaction, separate from the build's, so
    details fetched before a build fails are kept.
    """

    def __init__(self, sessions: Callable[[], Session] = _default_sessions) -> None:
        self._sessions = sessions

    def get(self, source: str, tickers: list[str], max_age: timedelta) -> dict[str, Constituent]:
        oldest = datetime.now(timezone.utc) - max_age
        found: dict[str, Constituent] = {}
        with self._sessions() as db:
            for start in range(0, len(tickers), _BATCH):
                rows = db.execute(
                    select(CompanyDetail.ticker, CompanyDetail.data).where(
                        CompanyDetail.source == source,
                        CompanyDetail.ticker.in_(tickers[start : start + _BATCH]),
                        CompanyDetail.fetched_at >= oldest,
                        CompanyDetail.data.is_not(None),
                    )
                )
                for ticker, data in rows:
                    found[ticker] = Constituent.from_dict(data)
        return found

    def put(self, source: str, companies: list[Constituent]) -> None:
        if not companies:
            return
        now = datetime.now(timezone.utc)
        rows = [
            {
                "source": source,
                "ticker": c.ticker,
                "data": c.to_dict(),
                "fetched_at": now,
                "wanted_at": None,
            }
            for c in companies
        ]
        with self._sessions() as db:
            for start in range(0, len(rows), _BATCH):
                statement = insert(CompanyDetail).values(rows[start : start + _BATCH])
                db.execute(
                    statement.on_conflict_do_update(
                        index_elements=["source", "ticker"],
                        set_={
                            "data": statement.excluded.data,
                            "fetched_at": statement.excluded.fetched_at,
                            "wanted_at": None,
                        },
                    )
                )
            db.commit()

    def want(self, source: str, tickers: list[str]) -> None:
        if not tickers:
            return
        now = datetime.now(timezone.utc)
        with self._sessions() as db:
            for start in range(0, len(tickers), _BATCH):
                statement = insert(CompanyDetail).values(
                    [
                        {"source": source, "ticker": ticker, "wanted_at": now}
                        for ticker in tickers[start : start + _BATCH]
                    ]
                )
                db.execute(
                    statement.on_conflict_do_update(
                        index_elements=["source", "ticker"], set_={"wanted_at": now}
                    )
                )
            db.commit()

    def due(self, source: str, limit: int, max_age: timedelta = DEFAULT_MAX_AGE) -> list[str]:
        """Tickers to fetch next: those a build is waiting for, then the stalest."""
        oldest = datetime.now(timezone.utc) - max_age
        with self._sessions() as db:
            rows = db.execute(
                select(CompanyDetail.ticker)
                .where(
                    CompanyDetail.source == source,
                    or_(CompanyDetail.wanted_at.is_not(None), CompanyDetail.fetched_at < oldest),
                )
                .order_by(
                    CompanyDetail.wanted_at.asc().nulls_last(),
                    CompanyDetail.fetched_at.asc(),
                    CompanyDetail.ticker,
                )
                .limit(limit)
            )
            return [ticker for (ticker,) in rows]

    def give_up(self, source: str, tickers: list[str]) -> None:
        """
        Stop asking for tickers the source turned out to know nothing about.

        A ticker with no stored details is forgotten; one with details keeps
        them and is tried again when they next go stale.
        """
        if not tickers:
            return
        now = datetime.now(timezone.utc)
        with self._sessions() as db:
            mine = (CompanyDetail.source == source, CompanyDetail.ticker.in_(tickers))
            db.execute(delete(CompanyDetail).where(*mine, CompanyDetail.data.is_(None)))
            db.execute(update(CompanyDetail).where(*mine).values(wanted_at=None, fetched_at=now))
            db.commit()


def fill_company_details(
    connector: DataConnector, store: DatabaseCompanyStore, limit: int
) -> dict[str, Any]:
    """
    Fetch details for up to `limit` companies that are wanted or stale.

    Runs on a schedule, a little at a time, so the store fills and stays fresh
    without sending the source a burst it would refuse. Stops at the first sign
    the source is limiting requests; the rest waits for the next run.
    """
    source = connector.get_name()
    tickers = store.due(source, limit)
    fetched = 0
    unknown = 0
    for start in range(0, len(tickers), _FILL_STEP):
        step = tickers[start : start + _FILL_STEP]
        try:
            companies = connector.get_constituent_data(step)
        except DataSourceError as e:
            logger.warning("Company details: %s stopped answering (%s)", source, e)
            return {"status": "limited", "fetched": fetched, "due": len(tickers)}
        known = [c for c in companies if c.market_cap or c.business_description]
        store.put(source, known)
        store.give_up(source, sorted(set(step) - {c.ticker for c in known}))
        fetched += len(known)
        unknown += len(step) - len(known)
    return {"status": "completed", "fetched": fetched, "unknown": unknown, "due": len(tickers)}
