"""
Backtest service.

Runs historical backtests for indices and calculates performance metrics.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.backtest import Backtest, BacktestResult, BacktestStatus
from app.models.index import Index, WeightingMethod
from app.services import index_math, rebalance_calendar
from app.services.index_math import Holding, IndexMathError
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

# Surfaced with every backtest. The number this qualifies is the one people use to
# decide whether to allocate, so the caveat travels with it rather than living in a
# docstring nobody reads.
SURVIVORSHIP_NOTE = (
    "Results use the index's current constituents applied to historical prices. "
    "Companies that were eligible during the period but have since been removed, "
    "delisted or acquired are not represented, so returns are optimistic. "
    "Point-in-time constituent history is required to remove this bias."
)


class BacktestService:
    """
    Service for running backtests.

    Simulates historical index performance using actual market data.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.market_data = MarketDataService()

    async def run_backtest(self, backtest_id: str) -> None:
        """
        Run a backtest.

        Args:
            backtest_id: ID of the backtest to run
        """
        # Load backtest with index
        result = await self.db.execute(
            select(Backtest)
            .where(Backtest.id == backtest_id)
            .options(selectinload(Backtest.index).selectinload(Index.components))
        )
        backtest = result.scalar_one_or_none()

        if not backtest:
            return

        try:
            # Update status
            backtest.status = BacktestStatus.RUNNING.value
            backtest.progress = 0.0
            await self.db.commit()

            # Get components
            components = [c for c in backtest.index.components if c.is_active]

            if not components:
                raise ValueError("No active components in index")

            tickers = [c.ticker for c in components]

            # Fetch historical prices
            prices = await self.market_data.get_prices_for_tickers(
                tickers,
                backtest.start_date,
                backtest.end_date,
            )

            if not prices:
                raise ValueError("Could not fetch price data")

            backtest.progress = 20.0
            await self.db.commit()

            # Fetch benchmark if specified
            benchmark_prices = None
            if backtest.benchmark_ticker:
                benchmark_data = await self.market_data.get_prices_for_tickers(
                    [backtest.benchmark_ticker],
                    backtest.start_date,
                    backtest.end_date,
                )
                if backtest.benchmark_ticker in benchmark_data:
                    benchmark_prices = benchmark_data[backtest.benchmark_ticker]

            backtest.progress = 40.0
            await self.db.commit()

            # Run simulation
            results = await self._simulate(
                backtest,
                components,
                prices,
                benchmark_prices,
            )

            backtest.progress = 80.0
            await self.db.commit()

            # Calculate summary statistics
            await self._calculate_statistics(backtest, results)

            # Mark complete
            backtest.status = BacktestStatus.COMPLETED.value
            backtest.progress = 100.0
            backtest.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            backtest.status = BacktestStatus.FAILED.value
            backtest.error_message = str(e)

        await self.db.commit()

    async def _simulate(
        self,
        backtest: Backtest,
        components: list,
        prices: dict[str, list[dict[str, Any]]],
        benchmark_prices: list[dict[str, Any]] | None,
    ) -> list[BacktestResult]:
        """
        Simulate the backtest.

        The portfolio holds a fixed share count between rebalances and reallocates to
        the methodology's target weights on the index's rebalancing schedule. This is
        what an index actually does: weights drift with prices between rebalances,
        rather than being silently reset to their starting values every day.

        Known limitation -- survivorship bias: the constituent list is the index's
        *current* membership, so the simulation selects today's survivors and runs
        them backwards. Correcting this requires point-in-time constituent history,
        which the free data connectors do not provide. Returns are therefore
        optimistic and should not be presented as achievable. See SURVIVORSHIP_NOTE.

        Args:
            backtest: Backtest configuration
            components: Index components
            prices: Historical prices by ticker
            benchmark_prices: Benchmark price history

        Returns:
            List of daily results
        """
        price_data: dict[str, dict[str, float]] = {}
        for ticker, history in prices.items():
            for row in history:
                day = row["date"]
                if row.get("close") and row["close"] > 0:
                    price_data.setdefault(day, {})[ticker] = row["close"]

        dates = sorted(price_data.keys())
        if not dates:
            return []

        components_by_ticker = {c.ticker: c for c in components}
        rebalance_days = rebalance_calendar.rebalance_dates(
            [datetime.strptime(d, "%Y-%m-%d").date() for d in dates],
            backtest.index.rebalance_frequency,
        )

        # Inception: establish holdings from the target weights as of day one.
        opening_prices = price_data[dates[0]]
        opening_targets = self._target_weights(
            backtest.index.weighting_method,
            components_by_ticker,
            opening_prices,
            opening_prices,
        )
        if not opening_targets:
            return []

        try:
            holdings, divisor = index_math.inception(
                target_weights=opening_targets,
                prices=opening_prices,
                base_value=backtest.initial_value,
            )
        except IndexMathError:
            logger.exception("Backtest %s could not establish opening holdings", backtest.id)
            return []

        results: list[BacktestResult] = []
        portfolio_value = backtest.initial_value
        peak_value = portfolio_value
        prev_value = portfolio_value

        benchmark_lookup: dict[str, float] = {}
        if benchmark_prices:
            for row in benchmark_prices:
                benchmark_lookup[row["date"]] = row["close"]
        benchmark_initial = benchmark_lookup.get(dates[0], 0)

        for day in dates:
            day_prices = price_data[day]

            # Reprice the existing share counts. A constituent with no print today
            # keeps yesterday's price rather than dropping out of the index.
            holdings = [
                Holding(
                    ticker=h.ticker,
                    price=day_prices.get(h.ticker, h.price),
                    shares=h.shares,
                )
                for h in holdings
            ]

            portfolio_value = index_math.index_level(holdings, divisor)

            if datetime.strptime(day, "%Y-%m-%d").date() in rebalance_days:
                holdings, divisor, cost = self._rebalance(
                    backtest, holdings, divisor, components_by_ticker, day_prices, opening_prices
                )
                # Costs are charged by shrinking the divisor's counterpart: the level
                # itself must absorb them, since a rebalance an investor pays for is
                # not free in the index they are tracking.
                if cost:
                    portfolio_value = index_math.index_level(holdings, divisor) * (1 - cost)
                    divisor = index_math.divisor_for_level(holdings, portfolio_value)

            day_return = (portfolio_value - prev_value) / prev_value if prev_value > 0 else 0.0
            prev_value = portfolio_value

            peak_value = max(peak_value, portfolio_value)
            drawdown = (peak_value - portfolio_value) / peak_value if peak_value > 0 else 0

            cum_return = (portfolio_value - backtest.initial_value) / backtest.initial_value

            benchmark_value = None
            benchmark_return = None
            excess_return = None

            if benchmark_initial > 0 and day in benchmark_lookup:
                benchmark_value = benchmark_lookup[day] / benchmark_initial * backtest.initial_value
                benchmark_return = (
                    benchmark_value - backtest.initial_value
                ) / backtest.initial_value
                excess_return = cum_return - benchmark_return

            result = BacktestResult(
                backtest_id=backtest.id,
                date=datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc),
                portfolio_value=portfolio_value,
                daily_return=day_return,
                cumulative_return=cum_return,
                drawdown=drawdown,
                benchmark_value=benchmark_value,
                benchmark_return=benchmark_return,
                excess_return=excess_return,
                holdings=index_math.weights(holdings),
            )
            results.append(result)
            self.db.add(result)

        return results

    def _rebalance(
        self,
        backtest: Backtest,
        holdings: list[Holding],
        divisor: float,
        components_by_ticker: dict[str, Any],
        day_prices: dict[str, float],
        opening_prices: dict[str, float],
    ) -> tuple[list[Holding], float, float]:
        """
        Reallocate to target weights, returning the new state and the turnover cost.

        On failure the previous holdings are kept: a rebalance that cannot be priced
        should leave the portfolio alone rather than abandon the simulation.
        """
        targets = self._target_weights(
            backtest.index.weighting_method,
            components_by_ticker,
            day_prices,
            opening_prices,
        )
        if not targets:
            return holdings, divisor, 0.0

        before = index_math.weights(holdings)

        try:
            new_holdings, new_divisor = index_math.rebalance(
                current=holdings,
                target_weights=targets,
                prices=day_prices,
                divisor=divisor,
            )
        except IndexMathError:
            logger.warning("Backtest %s: rebalance skipped, holdings unpriceable", backtest.id)
            return holdings, divisor, 0.0

        after = index_math.weights(new_holdings)
        turnover = (
            sum(abs(after.get(t, 0.0) - before.get(t, 0.0)) for t in set(before) | set(after)) / 2
        )

        return new_holdings, new_divisor, turnover * (settings.TRANSACTION_COST_BPS / 10_000)

    def _target_weights(
        self,
        method: str,
        components_by_ticker: dict[str, Any],
        day_prices: dict[str, float],
        opening_prices: dict[str, float],
    ) -> dict[str, float]:
        """
        Target weights as of a given day.

        Cap weighting uses market cap *as of that day*, approximated by scaling each
        constituent's stored market cap by its price move since the start of the
        window. Using the stored market cap directly would apply today's company
        sizes at every historical date -- a look-ahead that systematically
        overweights whichever names grew the most.

        Shares outstanding are assumed constant over the window, which is the usual
        approximation when a point-in-time shares series is unavailable.
        """
        tickers = [t for t in components_by_ticker if t in day_prices]
        if not tickers:
            return {}

        if method in (
            WeightingMethod.MARKET_CAP.value,
            WeightingMethod.FREE_FLOAT_MARKET_CAP.value,
        ):
            caps: dict[str, float] = {}
            for ticker in tickers:
                component = components_by_ticker[ticker]
                base_cap = component.market_cap or 0
                opening = opening_prices.get(ticker)
                if base_cap > 0 and opening and opening > 0:
                    caps[ticker] = base_cap * (day_prices[ticker] / opening)

            total = sum(caps.values())
            if total > 0:
                return {ticker: cap / total for ticker, cap in caps.items()}

        return dict.fromkeys(tickers, 1.0 / len(tickers))

    async def _calculate_statistics(
        self,
        backtest: Backtest,
        results: list[BacktestResult],
    ) -> None:
        """
        Calculate summary statistics from backtest results.
        """
        if not results:
            return

        # Convert to pandas for easier calculation
        returns = [r.daily_return for r in results]
        values = [r.portfolio_value for r in results]

        df = pd.DataFrame({"return": returns, "value": values})

        # Total return
        backtest.final_value = results[-1].portfolio_value
        backtest.total_return = results[-1].cumulative_return

        # Annualized return
        trading_days = len(results)
        years = trading_days / 252
        if years > 0 and backtest.total_return is not None:
            backtest.annualized_return = (1 + backtest.total_return) ** (1 / years) - 1

        # Volatility (annualized)
        if len(returns) > 1:
            backtest.volatility = float(df["return"].std() * math.sqrt(252))

        # Sharpe ratio (assuming 0% risk-free rate)
        if backtest.volatility and backtest.volatility > 0 and backtest.annualized_return:
            backtest.sharpe_ratio = backtest.annualized_return / backtest.volatility

        # Max drawdown
        backtest.max_drawdown = max(r.drawdown for r in results)

        # Benchmark return
        if results[-1].benchmark_return is not None:
            backtest.benchmark_return = results[-1].benchmark_return

        # Store time series for charts
        backtest.daily_values = {r.date.strftime("%Y-%m-%d"): r.portfolio_value for r in results}
        backtest.benchmark_values = {
            r.date.strftime("%Y-%m-%d"): r.benchmark_value
            for r in results
            if r.benchmark_value is not None
        }
        backtest.drawdown_series = {r.date.strftime("%Y-%m-%d"): r.drawdown for r in results}
