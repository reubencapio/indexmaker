"""
OpenBB data connector.

A free, open-source data connector using the OpenBB Platform.
OpenBB provides stock screening, fundamentals, and market data.

Installation:
    pip install openbb

For more info: https://openbb.co/
"""

import logging
from typing import Any, Optional, cast

import pandas as pd

from indexforge.core.constituent import Constituent
from indexforge.core.types import Currency
from indexforge.data.connectors.base import DataConnector

logger = logging.getLogger(__name__)


class OpenBBConnector(DataConnector):
    """
    Data connector for OpenBB Platform (free, open-source).

    OpenBB is an open-source alternative to Bloomberg Terminal.
    It aggregates data from multiple free sources and provides
    a unified API for financial data.

    Features:
    - Stock screening by sector, country, market cap
    - Historical prices
    - Fundamentals (P/E, market cap, etc.)
    - Company profiles
    - Free to use

    Example:
        >>> connector = OpenBBConnector()
        >>>
        >>> # Screen for Chinese tech stocks
        >>> stocks = connector.screen_stocks(country="CN", sector="Technology")
        >>>
        >>> # Get constituent data
        >>> constituents = connector.get_constituent_data(["BABA", "JD", "PDD"])
    """

    def __init__(self, provider: str = "yfinance") -> None:
        """
        Initialize OpenBB connector.

        Args:
            provider: Data provider to use (default: "yfinance")
                     Options: "yfinance", "fmp", "polygon", "intrinio"
        """
        self._provider = provider
        self._obb = None
        self._price_cache: dict[str, pd.DataFrame] = {}

    def _get_openbb(self):
        """Lazy load OpenBB to avoid import errors if not installed."""
        if self._obb is None:
            try:
                from openbb import obb

                self._obb = obb
            except ImportError:
                raise ImportError(
                    "OpenBB is required for OpenBBConnector. " "Install it with: pip install openbb"
                )
        return self._obb

    def screen_stocks(
        self,
        country: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Screen stocks by various criteria.

        This is a key feature that Yahoo Finance doesn't offer!

        Args:
            country: Country code (e.g., "CN", "US", "DE")
            sector: Sector name (e.g., "Technology", "Healthcare")
            industry: Industry name
            min_market_cap: Minimum market cap in USD
            max_market_cap: Maximum market cap in USD
            min_price: Minimum stock price
            max_price: Maximum stock price
            limit: Maximum number of results

        Returns:
            List of stock dictionaries with ticker, name, sector, etc.

        Example:
            >>> connector = OpenBBConnector()
            >>> chinese_tech = connector.screen_stocks(
            ...     country="CN",
            ...     sector="Technology",
            ...     min_market_cap=1_000_000_000
            ... )
        """
        obb = self._get_openbb()

        try:
            # Build screening parameters
            params = {"limit": limit, "provider": self._provider}

            if country:
                params["country"] = country
            if sector:
                params["sector"] = sector
            if industry:
                params["industry"] = industry
            if min_market_cap:
                params["mktcap_min"] = min_market_cap
            if max_market_cap:
                params["mktcap_max"] = max_market_cap
            if min_price:
                params["price_min"] = min_price
            if max_price:
                params["price_max"] = max_price

            # Use equity screener
            result = obb.equity.screener(**params)

            if hasattr(result, "to_df"):
                df = result.to_df()
                return cast(list[dict[str, Any]], df.to_dict("records"))
            elif hasattr(result, "results"):
                return [r.model_dump() for r in result.results]
            else:
                return []

        except Exception as e:
            logger.warning(f"Stock screening failed: {e}")
            # Fallback: try to get a list of stocks from search
            return self._fallback_screen(country, sector, limit)

    def _fallback_screen(
        self, country: Optional[str], sector: Optional[str], limit: int
    ) -> list[dict]:
        """Fallback screening using search if screener not available."""
        obb = self._get_openbb()

        # Map country codes to common search terms
        country_searches = {
            "CN": ["alibaba", "baidu", "jd.com", "nio", "xpeng", "bilibili"],
            "US": ["apple", "microsoft", "google", "amazon", "nvidia"],
            "DE": ["volkswagen", "siemens", "sap", "deutsche bank"],
            "JP": ["toyota", "sony", "nintendo", "softbank"],
        }

        results = []
        if country:
            search_terms = country_searches.get(country, ["technology"])
        else:
            search_terms = ["technology"]

        for term in search_terms[:limit]:
            try:
                search_result = obb.equity.search(term, provider="sec")
                if hasattr(search_result, "to_df"):
                    df = search_result.to_df()
                    if not df.empty:
                        results.extend(df.head(5).to_dict("records"))
            except Exception:
                continue

        return results[:limit]

    def get_prices(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical prices from OpenBB.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data for each ticker
        """
        obb = self._get_openbb()

        try:
            result = obb.equity.price.historical(
                symbol=",".join(tickers),
                start_date=start_date,
                end_date=end_date,
                provider=self._provider,
            )

            if hasattr(result, "to_df"):
                return result.to_df()
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return pd.DataFrame()

    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> list[Constituent]:
        """
        Fetch constituent data from OpenBB.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data (ignored, uses latest)

        Returns:
            List of Constituent objects
        """
        obb = self._get_openbb()
        constituents = []

        for ticker in tickers:
            try:
                # Get company profile
                profile = obb.equity.profile(ticker, provider=self._provider)

                if hasattr(profile, "to_df"):
                    df = profile.to_df()
                    if not df.empty:
                        info = df.iloc[0].to_dict()
                    else:
                        info = {}
                elif hasattr(profile, "results") and profile.results:
                    info = profile.results[0].model_dump() if profile.results else {}
                else:
                    info = {}

                # Get current quote for price
                try:
                    quote = obb.equity.price.quote(ticker, provider=self._provider)
                    if hasattr(quote, "to_df"):
                        quote_df = quote.to_df()
                        if not quote_df.empty:
                            price = quote_df.iloc[0].get("last_price") or quote_df.iloc[0].get(
                                "close"
                            )
                        else:
                            price = None
                    else:
                        price = None
                except Exception:
                    price = None

                constituent = Constituent(
                    ticker=ticker,
                    name=info.get("name", info.get("long_name", ticker)),
                    market_cap=info.get("market_cap", 0) or 0,
                    sector=info.get("sector", "Unknown"),
                    industry=info.get("industry", "Unknown"),
                    country=info.get("country", "Unknown"),
                    currency=Currency.USD,
                    exchange=info.get("exchange", ""),
                    price=price,
                    dividend_yield=info.get("dividend_yield", 0) or 0,
                    pe_ratio=info.get("pe_ratio"),
                    average_daily_volume=info.get("volume_avg", 0) or 0,
                    business_description=info.get(
                        "long_business_summary", info.get("description", "")
                    )
                    or "",
                )

                constituents.append(constituent)

            except Exception as e:
                logger.warning(f"Error fetching data for {ticker}: {e}")
                constituents.append(Constituent(ticker=ticker, name=ticker))

        return constituents

    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """
        Fetch market capitalization for tickers.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data

        Returns:
            Dictionary mapping ticker to market cap
        """
        constituents = self.get_constituent_data(tickers, as_of_date)
        return {c.ticker: c.market_cap for c in constituents}

    def get_sector(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch sector classification for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to sector
        """
        constituents = self.get_constituent_data(tickers)
        return {c.ticker: c.sector for c in constituents}

    def get_country(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch country of incorporation for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to country
        """
        constituents = self.get_constituent_data(tickers)
        return {c.ticker: c.country for c in constituents}

    def get_business_descriptions(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch business descriptions for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to business description
        """
        constituents = self.get_constituent_data(tickers)
        return {c.ticker: c.business_description for c in constituents}

    def search_stocks(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search for stocks by name or ticker.

        Args:
            query: Search query (company name or ticker)
            limit: Maximum results

        Returns:
            List of matching stocks
        """
        obb = self._get_openbb()

        try:
            result = obb.equity.search(query, provider="sec")
            if hasattr(result, "to_df"):
                df = result.to_df()
                return cast(list[dict[str, Any]], df.head(limit).to_dict("records"))
            return []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []

    def get_index_constituents(self, index: str) -> list[str]:
        """
        Get constituents of a major index.

        Args:
            index: Index symbol (e.g., "^GSPC" for S&P 500)

        Returns:
            List of ticker symbols
        """
        obb = self._get_openbb()

        # Map common index names
        index_map = {
            "SP500": "^GSPC",
            "NASDAQ100": "^NDX",
            "DOW": "^DJI",
            "FTSE100": "^FTSE",
            "DAX": "^GDAXI",
        }

        index_symbol = index_map.get(index.upper(), index)

        try:
            result = obb.index.constituents(index_symbol, provider=self._provider)
            if hasattr(result, "to_df"):
                df = result.to_df()
                if "symbol" in df.columns:
                    return cast(list[str], df["symbol"].tolist())
            return []
        except Exception as e:
            logger.warning(f"Could not get index constituents: {e}")
            return []

    def is_available(self) -> bool:
        """Check if OpenBB is available."""
        try:
            self._get_openbb()
            return True
        except ImportError:
            return False

    def get_name(self) -> str:
        """Get connector name."""
        return f"OpenBB ({self._provider})"

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._price_cache.clear()
