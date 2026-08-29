import logging
from datetime import date
from typing import Any

from asgiref.sync import async_to_sync

from app.api.v1.endpoints.market_data_providers import get_user_connector
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.index import Index, IndexComponent, IndexStatus
from app.services.llm_service import generate_index_config_from_llm

logger = logging.getLogger(__name__)

# Failure text is surfaced to the index owner, so keep it short enough to render
# in a status pill without truncating mid-word in the middle of the UI.
MAX_ERROR_MESSAGE_LENGTH = 500

# Base delay before the first retry; doubles on each subsequent attempt.
RETRY_BACKOFF_SECONDS = 20

# Substrings that mark a failure as worth retrying. Deliberately conservative:
# retrying a permanent error (a retired model, a bad key, a malformed prompt) burns
# quota and delays the user seeing the real reason. Anything not listed here is
# treated as permanent and surfaced immediately.
TRANSIENT_ERROR_MARKERS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "timeout",
    "timed out",
    "deadline exceeded",
    "temporarily unavailable",
    "overloaded",
    "rate limit",
    "connection reset",
    "connection aborted",
)


def is_transient_error(message: str) -> bool:
    """True if a failure looks worth retrying rather than reporting."""
    lowered = message.lower()
    return any(marker in lowered for marker in TRANSIENT_ERROR_MARKERS)


def _mark_index_building(index_id: str) -> None:
    """Return an index to the building state ahead of a retry."""
    db = SessionLocal()
    try:
        index = db.query(Index).filter(Index.id == str(index_id)).first()
        if index:
            index.status = IndexStatus.BUILDING.value
            index.error_message = None
            db.commit()
    except Exception:  # pragma: no cover - best-effort bookkeeping
        logger.exception("Could not return index %s to building", index_id)
    finally:
        db.close()


def _mark_index_error(index_id: str, message: str) -> None:
    """
    Record a generation failure on the index.

    Opens its own session: the caller's session may already be closed by the time
    a failure surfaces, and leaving the index stuck in "building" forever is worse
    than the failure itself.
    """
    db = SessionLocal()
    try:
        index = db.query(Index).filter(Index.id == str(index_id)).first()
        if index:
            index.status = IndexStatus.ERROR.value
            index.error_message = message[:MAX_ERROR_MESSAGE_LENGTH]
            db.commit()
    except Exception:  # pragma: no cover - best-effort bookkeeping
        logger.exception("Could not mark index %s as errored", index_id)
    finally:
        db.close()


async def populate_index_components(
    index_id: str,
    user_id: str,
    tickers: list[str],
    weighting_method: str,
    max_weight: float | None,
    theme_keywords: list[str] | None = None,
    max_components: int | None = None,
) -> dict[str, Any]:
    """
    Async logic to fetch market data and populate index components.
    This runs inside the Celery worker.
    """
    db = SessionLocal()
    try:
        components_added = 0
        data_source_name = "OpenBB"  # Default
        market_data = {}

        # 1. Fetch Market Data
        if tickers:
            try:
                # We need to run the async connector methods in a sync context if they are async
                # Check if get_user_connector returns a sync or async connector
                connector = get_user_connector(user_id)
                data_source_name = connector.get_name()

                # Assuming get_constituent_data is synchronous or we need to handle it
                # Based on previous code in ai.py usage, it seemed synchronous,
                # but if it was awaited in ai.py, we need to check.
                # In ai.py: constituents = connector.get_constituent_data(tickers) (no await shown in previous snippet?)
                # Wait, looking at ai.py snippet:
                # `constituents = connector.get_constituent_data(tickers)` was NOT awaited in the original code.
                # So it's synchronous.

                constituents = connector.get_constituent_data(tickers)
                market_data = {c.ticker: c for c in constituents}
                logger.info(
                    f"Fetched market data for {len(market_data)} tickers from {data_source_name}"
                )
            except Exception as e:
                logger.warning(f"Could not fetch market data: {e}")
                # No fallback needed - the LocalOpenBBConnector handles this internally

            # 2. Apply Theme Filtering (filtered only if we have good matches, otherwise trust LLM)
            if theme_keywords and market_data:
                logger.info(f"Applying theme filter with keywords: {theme_keywords}")

                # Calculate match score for logging, but don't strictly filter out
                # trusted LLM selections unless we are sure.
                # For now, we'll keep all tickers provided by LLM as strict filtering
                # removes valid companies (e.g. MSFT/GOOG for 'quantum')

                # Check matches just for logging stats
                matches = 0
                for _, constituent in market_data.items():
                    searchable_text = " ".join(
                        [
                            constituent.business_description or "",
                            constituent.industry or "",
                            constituent.name or "",
                        ]
                    ).lower()
                    if any(kw.lower() in searchable_text for kw in theme_keywords):
                        matches += 1

                logger.info(
                    f"Theme keywords matched {matches}/{len(market_data)} tickers (keeping all)"
                )

                # Limit to max_components if specified (still sorting by market cap)
                if max_components and len(tickers) > max_components:
                    # Sort by market cap and take top N
                    tickers = sorted(
                        tickers,
                        key=lambda t: market_data.get(
                            t, type("obj", (object,), {"market_cap": 0})
                        ).market_cap
                        or 0,
                        reverse=True,
                    )[:max_components]
                    logger.info(f"Limited to top {max_components} by market cap")

            # 2. Calculate Weights
            if weighting_method == "equal_weight":
                weights = {t: 1.0 / len(tickers) for t in tickers}
            elif weighting_method in ("market_cap", "free_float_market_cap"):
                total_market_cap = sum(
                    market_data.get(t.upper(), type("obj", (object,), {"market_cap": 0})).market_cap
                    for t in tickers
                )
                if total_market_cap > 0:
                    weights = {
                        t: market_data.get(
                            t.upper(), type("obj", (object,), {"market_cap": 0})
                        ).market_cap
                        / total_market_cap
                        for t in tickers
                    }
                else:
                    weights = {t: 1.0 / len(tickers) for t in tickers}
            else:
                weights = {t: 1.0 / len(tickers) for t in tickers}

            # Apply max weight cap
            if max_weight:
                for ticker in weights:
                    if weights[ticker] > max_weight:
                        weights[ticker] = max_weight

            # 3. Save Components to DB
            for ticker in tickers:
                ticker_upper = ticker.upper()
                constituent = market_data.get(ticker_upper)

                component = IndexComponent(
                    index_id=str(index_id),
                    ticker=ticker_upper,
                    name=constituent.name if constituent else ticker_upper,
                    sector=constituent.sector if constituent else None,
                    industry=constituent.industry if constituent else None,
                    country=constituent.country if constituent else None,
                    market_cap=constituent.market_cap if constituent else None,
                    price=constituent.price if constituent else None,
                    avg_volume=constituent.average_daily_volume if constituent else None,
                    weight=weights.get(ticker, 0),
                    target_weight=weights.get(ticker, 0),
                    is_active=True,
                )
                db.add(component)
                components_added += 1

            db.commit()

        return {
            "components_added": components_added,
            "data_source": data_source_name,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Error in background task: {e}")
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(name="populate_index_with_components")
def populate_index_with_components_task(
    index_id: str, user_id: str, tickers: list[str], weighting_method: str, max_weight: float | None
):
    """
    Celery task wrapper for async index population.
    """
    # Run the async logic synchronously since Celery tasks are sync by default
    # But wait, our logic above is defined as async def but mostly uses sync DB and sync connectors.
    # The only async part might be if we upgraded connectors.
    # For now, let's keep it simple. If populate_index_components is async, we run it:
    return async_to_sync(populate_index_components)(
        index_id, user_id, tickers, weighting_method, max_weight
    )


async def generate_and_populate_index(
    index_id: str,
    user_id: str,
    description: str,
    base_value: float,
    base_date: str | None,
) -> dict[str, Any]:
    """
    Async logic to generate config AND populate components.
    """
    db = SessionLocal()
    try:
        # 1. Generate Config using LLM Service
        try:
            config = await generate_index_config_from_llm(description, base_value, base_date)
        except Exception as e:
            logger.exception("LLM generation failed for index %s", index_id)
            db.close()
            _mark_index_error(index_id, f"AI generation failed: {e}")
            return {"status": "failed", "error": str(e)}

        # 2. Update Index in DB
        index = db.query(Index).filter(Index.id == str(index_id)).first()
        if not index:
            logger.error(f"Index {index_id} not found")
            db.close()
            return {"status": "failed", "error": "Index not found"}

        # Update fields from config
        index.name = config.get("name", index.name)
        index.identifier = config.get("identifier", index.identifier)
        index.description = config.get("description", index.description)
        index.currency = config.get("currency", index.currency)
        if config.get("base_date"):
            index.base_date = date.fromisoformat(config["base_date"])
        # index.base_value = config.get("base_value") # Already set on creation?
        index.countries = config.get("countries")
        index.sectors = config.get("sectors")
        index.min_market_cap = config.get("min_market_cap")
        index.max_components = config.get("max_components")
        index.weighting_method = config.get("weighting_method")
        index.max_weight = config.get("max_weight")
        index.rebalance_frequency = config.get("rebalance_frequency")
        # Store theme_keywords in custom_rules so they're available when editing
        custom_rules = config.get("custom_rules") or {}
        theme_keywords = config.get("theme_keywords", [])
        if theme_keywords:
            custom_rules["theme_keywords"] = theme_keywords
        index.custom_rules = custom_rules
        # Ensure status is building, and clear any failure from a previous attempt
        index.status = IndexStatus.BUILDING.value
        index.error_message = None

        db.commit()

        # 3. Populate Components
        # We can call the logic directly or helper
        # Reuse populate_index_components logic by calling it
        # But we need to use the tickers from config
        tickers = config.get("tickers", [])

        # Capture values before closing session
        weighting_method = index.weighting_method
        max_weight = index.max_weight
        max_components = index.max_components
        theme_keywords = config.get("theme_keywords", [])
        logger.info(f"LLM config: theme_keywords={theme_keywords}, tickers={len(tickers)}")

        # Close this DB session before calling the next function
        db.close()

        result = await populate_index_components(
            index_id=index_id,
            user_id=user_id,
            tickers=tickers,
            weighting_method=weighting_method,
            max_weight=max_weight,
            theme_keywords=theme_keywords if theme_keywords else None,
            max_components=max_components,
        )

        # 4. Mark Index as ACTIVE
        # We need a fresh session to update the status
        db_final = SessionLocal()
        try:
            index_final = db_final.query(Index).filter(Index.id == str(index_id)).first()
            if index_final:
                index_final.status = IndexStatus.ACTIVE.value
                index_final.error_message = None
                db_final.commit()
        finally:
            db_final.close()

        return result

    except Exception as e:
        logger.exception("Error in generate_and_populate task for index %s", index_id)
        # Without this the index stays in "building" forever and the UI spins
        # against a task that is no longer running.
        _mark_index_error(index_id, f"Index generation failed: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="generate_and_populate_index", bind=True, max_retries=3)
def generate_and_populate_index_task(
    self,
    index_id: str,
    user_id: str,
    description: str,
    base_value: float = 1000.0,
    base_date: str | None = None,
):
    """
    Celery task for full async generation.

    Retries transient provider failures with a backoff. The inner coroutine catches
    its own exceptions and reports failure in the return value rather than raising,
    so the retry decision is made here by inspecting that result.
    """
    result = async_to_sync(generate_and_populate_index)(
        index_id, user_id, description, base_value, base_date
    )

    if (
        isinstance(result, dict)
        and result.get("status") == "failed"
        and is_transient_error(result.get("error", ""))
        and self.request.retries < self.max_retries
    ):
        delay = RETRY_BACKOFF_SECONDS * (2**self.request.retries)
        logger.warning(
            "Index %s generation failed transiently; retry %d in %ds",
            index_id,
            self.request.retries + 1,
            delay,
        )
        # Put the index back into "building" so the UI keeps showing progress
        # rather than flashing a failure that is about to be retried anyway.
        _mark_index_building(index_id)
        raise self.retry(countdown=delay)

    return result


# =====================================
# Backtest Tasks
# =====================================


async def run_backtest_async(backtest_id: str) -> dict[str, Any]:
    """
    Async logic to run a backtest.
    This runs inside the Celery worker.
    """
    from app.db.session import async_session_maker
    from app.services.backtest_service import BacktestService

    async with async_session_maker() as db:
        service = BacktestService(db)
        await service.run_backtest(backtest_id)
        await db.commit()

    return {"status": "completed", "backtest_id": backtest_id}


@celery_app.task(name="run_backtest", bind=True, max_retries=1)
def run_backtest_task(self, backtest_id: str):
    """
    Celery task for running backtests asynchronously.

    This offloads the heavy backtest computation to a worker,
    preventing the API from blocking.
    """
    logger.info(f"Starting backtest task: {backtest_id}")
    try:
        result = async_to_sync(run_backtest_async)(backtest_id)
        logger.info(f"Backtest completed: {backtest_id}")
        return result
    except Exception as e:
        logger.error(f"Backtest failed: {backtest_id} - {e}")
        # Mark backtest as failed in DB
        from app.db.session import SessionLocal
        from app.models.backtest import Backtest, BacktestStatus

        db = SessionLocal()
        try:
            backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
            if backtest:
                backtest.status = BacktestStatus.FAILED.value
                backtest.error_message = str(e)
                db.commit()
        finally:
            db.close()
        raise


# =====================================
# Report Generation Tasks
# =====================================


async def generate_report_async(report_id: str) -> dict[str, Any]:
    """
    Async logic to generate a report.
    This runs inside the Celery worker.
    """
    import traceback
    from datetime import datetime, timezone

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.session import async_session_maker
    from app.models.index import Index
    from app.models.report import GeneratedReport, ReportStatus

    async with async_session_maker() as db:
        # Get the report
        result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
        report = result.scalar_one_or_none()

        if not report:
            return {"status": "error", "message": "Report not found"}

        try:
            # Mark as processing
            report.status = ReportStatus.GENERATING.value
            await db.commit()

            # Get index with components - need to re-fetch report after commit
            await db.refresh(report)

            result = await db.execute(
                select(Index)
                .where(Index.id == report.index_id)
                .options(
                    selectinload(Index.components),
                    selectinload(Index.snapshots),
                )
            )
            index = result.scalar_one_or_none()

            if not index:
                report.status = ReportStatus.FAILED.value
                report.error_message = "Index not found"
                await db.commit()
                return {"status": "error", "message": "Index not found"}

            # Import report generation functions
            from app.api.v1.endpoints.reports import (
                calculate_performance_metrics,
                generate_factsheet_html,
            )

            # Generate the report content
            metrics = calculate_performance_metrics(index)
            html_content = generate_factsheet_html(index, metrics)

            # Store metrics snapshot
            report.metrics_snapshot = metrics

            # For now, we don't store files - just mark complete
            # In production, you'd upload to S3 and store file_path/file_url
            report.file_size_bytes = len(html_content.encode())
            report.status = ReportStatus.COMPLETED.value
            report.completed_at = datetime.now(timezone.utc)

            await db.commit()

            logger.info(f"Report generated successfully: {report_id}")
            return {"status": "completed", "report_id": report_id}

        except Exception as e:
            logger.error(f"Report generation failed: {report_id}")
            logger.error(f"Exception: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())

            # Re-fetch the report in case the session is stale
            await db.rollback()
            result = await db.execute(
                select(GeneratedReport).where(GeneratedReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            if report:
                report.status = ReportStatus.FAILED.value
                report.error_message = f"{type(e).__name__}: {str(e)[:200]}"
                await db.commit()

            return {"status": "error", "message": str(e)}


@celery_app.task(name="generate_report", bind=True, max_retries=1)
def generate_report_task(self, report_id: str):
    """
    Celery task for generating reports asynchronously.

    This offloads report generation to a worker,
    preventing the API from blocking.
    """
    logger.info(f"Starting report generation task: {report_id}")
    try:
        result = async_to_sync(generate_report_async)(report_id)
        logger.info(f"Report generation completed: {report_id}")
        return result
    except Exception as e:
        logger.error(f"Report generation failed: {report_id} - {e}")
        # Mark report as failed in DB
        from app.db.session import SessionLocal
        from app.models.report import GeneratedReport, ReportStatus

        db = SessionLocal()
        try:
            report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
            if report:
                report.status = ReportStatus.FAILED.value
                report.error_message = str(e)
                db.commit()
        finally:
            db.close()
        raise
