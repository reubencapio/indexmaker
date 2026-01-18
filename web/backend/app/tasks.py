import logging
from datetime import date
from typing import Any

from asgiref.sync import async_to_sync

from app.api.v1.endpoints.market_data_providers import get_user_connector
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.index import Index, IndexComponent
from app.services.llm_service import generate_index_config_from_llm

logger = logging.getLogger(__name__)


async def populate_index_components(
    index_id: str, user_id: str, tickers: list[str], weighting_method: str, max_weight: float | None
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
                # Fallback
                try:
                    from indexmaker.data.connectors.yahoo import YahooFinanceConnector

                    connector = YahooFinanceConnector()
                    constituents = connector.get_constituent_data(tickers)
                    market_data = {c.ticker: c for c in constituents}
                    data_source_name = "Yahoo Finance (fallback)"
                    logger.info(
                        f"Fallback: Fetched market data for {len(market_data)} tickers from Yahoo Finance"
                    )
                except Exception as e2:
                    logger.warning(f"Fallback also failed: {e2}")

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
            logger.error(f"LLM Generation failed: {e}")
            # Mark index as error
            index = db.query(Index).filter(Index.id == str(index_id)).first()
            if index:
                index.status = "error"  # Assuming we add an error status or reuse 'archived'
                # index.description = f"Generation failed: {str(e)}"
                db.commit()
            return {"status": "failed", "error": str(e)}

        # 2. Update Index in DB
        index = db.query(Index).filter(Index.id == str(index_id)).first()
        if not index:
            logger.error(f"Index {index_id} not found")
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
        index.custom_rules = config.get("custom_rules")
        # Ensure status is building
        index.status = "building"

        db.commit()

        # 3. Populate Components
        # We can call the logic directly or helper
        # Reuse populate_index_components logic by calling it
        # But we need to use the tickers from config
        tickers = config.get("tickers", [])

        # Capture values before closing session
        weighting_method = index.weighting_method
        max_weight = index.max_weight

        # Close this DB session before calling the next function
        db.close()

        result = await populate_index_components(
            index_id=index_id,
            user_id=user_id,
            tickers=tickers,
            weighting_method=weighting_method,
            max_weight=max_weight,
        )

        # 4. Mark Index as ACTIVE
        # We need a fresh session to update the status
        db_final = SessionLocal()
        try:
            index_final = db_final.query(Index).filter(Index.id == str(index_id)).first()
            if index_final:
                index_final.status = "active"
                db_final.commit()
        finally:
            db_final.close()

        return result

    except Exception as e:
        logger.error(f"Error in generate_and_populate task: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        # Ensure DB is closed if not already
        pass


@celery_app.task(name="generate_and_populate_index")
def generate_and_populate_index_task(
    index_id: str,
    user_id: str,
    description: str,
    base_value: float = 1000.0,
    base_date: str | None = None,
):
    """
    Celery task for full async generation.
    """
    return async_to_sync(generate_and_populate_index)(
        index_id, user_id, description, base_value, base_date
    )
