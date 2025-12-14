"""
Market data service.

Fetches and caches market data from external sources (Yahoo Finance).
Uses the indexmaker library's data connectors.
"""

from datetime import datetime
from typing import Any

import yfinance as yf


class MarketDataService:
    """
    Service for fetching market data.

    Uses yfinance for free market data access.
    """

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    async def get_security_info(self, ticker: str) -> dict[str, Any] | None:
        """
        Get security information.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Security info dict or None if not found
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or info.get("regularMarketPrice") is None:
                return None

            return {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "currency": info.get("currency", "USD"),
                "market_cap": info.get("marketCap"),
                "price": info.get("regularMarketPrice"),
                "avg_volume": info.get("averageVolume"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
            }
        except Exception:
            return None

    async def get_price_history(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """
        Get historical price data.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date
            end_date: End date

        Returns:
            List of OHLCV data points
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
            )

            if hist.empty:
                return []

            result = []
            for date, row in hist.iterrows():
                result.append(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row["Volume"]),
                    }
                )
            return result
        except Exception:
            return []

    async def get_prices_for_tickers(
        self,
        tickers: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get historical prices for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            Dict mapping ticker to price history
        """
        try:
            data = yf.download(
                tickers,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                group_by="ticker",
                auto_adjust=True,
                progress=False,
            )

            if data.empty:
                return {}

            result: dict[str, list[dict[str, Any]]] = {}

            if len(tickers) == 1:
                # Single ticker - different structure
                ticker = tickers[0]
                result[ticker] = []
                for date, row in data.iterrows():
                    result[ticker].append(
                        {
                            "date": date.strftime("%Y-%m-%d"),
                            "close": float(row["Close"]),
                        }
                    )
            else:
                # Multiple tickers
                for ticker in tickers:
                    if ticker in data.columns.get_level_values(0):
                        ticker_data = data[ticker]
                        result[ticker] = []
                        for date, row in ticker_data.iterrows():
                            if not row.isna().all():
                                result[ticker].append(
                                    {
                                        "date": date.strftime("%Y-%m-%d"),
                                        "close": float(row["Close"]),
                                    }
                                )

            return result
        except Exception:
            return {}

    async def search_securities(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for securities.

        Note: yfinance doesn't have a search API, so we try to look up the query
        as a ticker directly. For production, use a proper search API.

        Args:
            query: Search term
            limit: Maximum results

        Returns:
            List of search results
        """
        # Try direct ticker lookup
        results = []
        try:
            stock = yf.Ticker(query.upper())
            info = stock.info
            if info and info.get("regularMarketPrice"):
                results.append(
                    {
                        "ticker": query.upper(),
                        "name": info.get("longName") or info.get("shortName", query),
                        "exchange": info.get("exchange"),
                        "type": info.get("quoteType"),
                    }
                )
        except Exception:
            pass

        return results[:limit]

