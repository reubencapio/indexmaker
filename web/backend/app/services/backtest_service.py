"""
Backtest service.

Runs historical backtests for indices and calculates performance metrics.
"""

import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.backtest import Backtest, BacktestResult, BacktestStatus
from app.models.index import Index, WeightingMethod
from app.services.market_data_service import MarketDataService


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

        Args:
            backtest: Backtest configuration
            components: Index components
            prices: Historical prices by ticker
            benchmark_prices: Benchmark price history

        Returns:
            List of daily results
        """
        # Build price DataFrames
        price_data: dict[str, dict[str, float]] = {}
        for ticker, history in prices.items():
            for row in history:
                date = row["date"]
                if date not in price_data:
                    price_data[date] = {}
                price_data[date][ticker] = row["close"]

        dates = sorted(price_data.keys())
        if not dates:
            return []

        # Calculate initial weights
        weights = await self._calculate_weights(
            backtest.index.weighting_method,
            components,
            price_data.get(dates[0], {}),
        )

        # Simulate daily values
        results: list[BacktestResult] = []
        portfolio_value = backtest.initial_value
        peak_value = portfolio_value
        prev_value = portfolio_value

        # Build benchmark lookup
        benchmark_lookup: dict[str, float] = {}
        if benchmark_prices:
            for row in benchmark_prices:
                benchmark_lookup[row["date"]] = row["close"]

        benchmark_initial = benchmark_lookup.get(dates[0], 0)

        for i, date in enumerate(dates):
            day_prices = price_data.get(date, {})

            # Calculate portfolio return
            day_return = 0.0
            for ticker, weight in weights.items():
                if ticker in day_prices:
                    curr_price = day_prices[ticker]
                    # Get previous price
                    prev_price = curr_price
                    if i > 0:
                        prev_day = dates[i - 1]
                        prev_prices = price_data.get(prev_day, {})
                        prev_price = prev_prices.get(ticker, curr_price)

                    if prev_price > 0:
                        ticker_return = (curr_price - prev_price) / prev_price
                        day_return += weight * ticker_return

            # Update portfolio value
            if i > 0:
                portfolio_value = prev_value * (1 + day_return)
            prev_value = portfolio_value

            # Track peak for drawdown
            peak_value = max(peak_value, portfolio_value)
            drawdown = (peak_value - portfolio_value) / peak_value if peak_value > 0 else 0

            # Cumulative return
            cum_return = (portfolio_value - backtest.initial_value) / backtest.initial_value

            # Benchmark values
            benchmark_value = None
            benchmark_return = None
            excess_return = None

            if benchmark_initial > 0 and date in benchmark_lookup:
                benchmark_value = (
                    benchmark_lookup[date] / benchmark_initial * backtest.initial_value
                )
                benchmark_return = (
                    benchmark_value - backtest.initial_value
                ) / backtest.initial_value
                excess_return = cum_return - benchmark_return

            result = BacktestResult(
                backtest_id=backtest.id,
                date=datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc),
                portfolio_value=portfolio_value,
                daily_return=day_return,
                cumulative_return=cum_return,
                drawdown=drawdown,
                benchmark_value=benchmark_value,
                benchmark_return=benchmark_return,
                excess_return=excess_return,
                holdings=weights,
            )
            results.append(result)
            self.db.add(result)

        return results

    async def _calculate_weights(
        self,
        method: str,
        components: list,
        prices: dict[str, float],
    ) -> dict[str, float]:
        """Calculate initial weights for components."""
        active = [c for c in components if c.ticker in prices]

        if not active:
            return {}

        if method == WeightingMethod.EQUAL_WEIGHT.value:
            weight = 1.0 / len(active)
            return {c.ticker: weight for c in active}

        elif method in [
            WeightingMethod.MARKET_CAP.value,
            WeightingMethod.FREE_FLOAT_MARKET_CAP.value,
        ]:
            total_mcap = sum(c.market_cap or 0 for c in active)
            if total_mcap > 0:
                return {c.ticker: (c.market_cap or 0) / total_mcap for c in active}

        # Default to equal weight
        weight = 1.0 / len(active)
        return {c.ticker: weight for c in active}

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
