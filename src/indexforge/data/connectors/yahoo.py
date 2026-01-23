"""
Yahoo Finance data connector.

A free data connector using the yfinance library.
"""

import logging
from typing import Optional

import pandas as pd

from indexforge.core.constituent import Constituent
from indexforge.core.types import Currency
from indexforge.data.connectors.base import DataConnector

logger = logging.getLogger(__name__)


class YahooFinanceConnector(DataConnector):
    """
    Data connector for Yahoo Finance (free data source).

    Uses the yfinance library to fetch market data, fundamentals,
    and corporate actions data.

    Features:
    - Historical prices (OHLCV)
    - Market capitalization
    - Basic fundamentals (sector, industry, country)
    - Dividend and split data
    - Free, no API key required

    Limitations:
    - Data is delayed 15-20 minutes
    - No intraday data on free tier
    - Rate limits exist (but generous)
    - Historical data may have gaps

    Example:
        >>> connector = YahooFinanceConnector()
        >>> prices = connector.get_prices(["AAPL", "MSFT"], "2024-01-01", "2024-12-31")
        >>> constituents = connector.get_constituent_data(["AAPL", "MSFT"])
    """

    def __init__(self, cache_enabled: bool = True) -> None:
        """
        Initialize Yahoo Finance connector.

        Args:
            cache_enabled: Whether to cache data locally (reduces API calls)
        """
        self._cache_enabled = cache_enabled
        self._price_cache: dict[str, pd.DataFrame] = {}
        self._info_cache: dict[str, dict] = {}
        self._yf = None

    def _get_yfinance(self):
        """Lazy load yfinance to avoid import errors if not installed."""
        if self._yf is None:
            try:
                import yfinance as yf

                self._yf = yf
            except ImportError:
                raise ImportError(
                    "yfinance is required for YahooFinanceConnector. "
                    "Install it with: pip install yfinance"
                )
        return self._yf

    def get_prices(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical prices from Yahoo Finance.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data for each ticker
        """
        yf = self._get_yfinance()

        try:
            # Download all tickers at once (more efficient)
            data = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )

            if data.empty:
                logger.warning(f"No data returned for {tickers}")
                return pd.DataFrame()

            # If single ticker, yfinance doesn't use MultiIndex
            if len(tickers) == 1:
                data.columns = pd.MultiIndex.from_product([[tickers[0]], data.columns])

            return data

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return pd.DataFrame()

    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> list[Constituent]:
        """
        Fetch constituent data from Yahoo Finance.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data (ignored, always uses latest)

        Returns:
            List of Constituent objects
        """
        yf = self._get_yfinance()
        constituents = []

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = self._get_stock_info(stock, ticker)

                constituent = Constituent(
                    ticker=ticker,
                    name=info.get("longName", info.get("shortName", ticker)),
                    market_cap=info.get("marketCap", 0) or 0,
                    sector=info.get("sector", "Unknown"),
                    industry=info.get("industry", "Unknown"),
                    country=info.get("country", "Unknown"),
                    currency=(
                        Currency(info.get("currency", "USD"))
                        if info.get("currency") in [c.value for c in Currency]
                        else Currency.USD
                    ),
                    exchange=info.get("exchange", ""),
                    dividend_yield=info.get("dividendYield", 0) or 0,
                    pe_ratio=info.get("trailingPE"),
                    pb_ratio=info.get("priceToBook"),
                    average_daily_volume=info.get("averageVolume", 0) or 0,
                    free_float_factor=self._calculate_free_float(info),
                    business_description=info.get("longBusinessSummary", "") or "",
                )

                # Calculate free float market cap
                constituent.free_float_market_cap = (
                    constituent.market_cap * constituent.free_float_factor
                )

                # Get current price
                hist = stock.history(period="1d")
                if not hist.empty:
                    constituent.price = hist["Close"].iloc[-1]

                constituents.append(constituent)

            except Exception as e:
                logger.warning(f"Error fetching data for {ticker}: {e}")
                # Create minimal constituent
                constituents.append(Constituent(ticker=ticker, name=ticker))

        return constituents

    def _get_stock_info(self, stock, ticker: str) -> dict:
        """Get stock info with caching."""
        if self._cache_enabled and ticker in self._info_cache:
            return self._info_cache[ticker]

        try:
            info: dict = stock.info
            if self._cache_enabled:
                self._info_cache[ticker] = info
            return info
        except Exception:
            return {}

    def _calculate_free_float(self, info: dict) -> float:
        """Calculate free float factor from Yahoo Finance data."""
        shares_outstanding: float = info.get("sharesOutstanding", 0) or 0
        float_shares: float = info.get("floatShares", 0) or 0

        if shares_outstanding and float_shares:
            return float(min(float_shares / shares_outstanding, 1.0))
        return 1.0  # Default to 100% free float

    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """
        Fetch market capitalization for tickers.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data (ignored, uses latest)

        Returns:
            Dictionary mapping ticker to market cap
        """
        yf = self._get_yfinance()
        market_caps = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = self._get_stock_info(stock, ticker)
                market_caps[ticker] = info.get("marketCap", 0) or 0
            except Exception as e:
                logger.warning(f"Error fetching market cap for {ticker}: {e}")
                market_caps[ticker] = 0

        return market_caps

    def get_dividends(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch dividend data.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with dividend data
        """
        yf = self._get_yfinance()
        all_dividends = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                dividends = stock.dividends

                # Filter by date range
                if not dividends.empty:
                    dividends = dividends[
                        (dividends.index >= start_date) & (dividends.index <= end_date)
                    ]
                    all_dividends[ticker] = dividends
            except Exception as e:
                logger.warning(f"Error fetching dividends for {ticker}: {e}")

        if not all_dividends:
            return pd.DataFrame()

        return pd.DataFrame(all_dividends)

    def get_splits(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch stock split data.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with split data
        """
        yf = self._get_yfinance()
        all_splits = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                splits = stock.splits

                # Filter by date range
                if not splits.empty:
                    splits = splits[(splits.index >= start_date) & (splits.index <= end_date)]
                    all_splits[ticker] = splits
            except Exception as e:
                logger.warning(f"Error fetching splits for {ticker}: {e}")

        if not all_splits:
            return pd.DataFrame()

        return pd.DataFrame(all_splits)

    def get_free_float(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """
        Fetch free float ratio for tickers.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data

        Returns:
            Dictionary mapping ticker to free float ratio
        """
        yf = self._get_yfinance()
        free_floats = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = self._get_stock_info(stock, ticker)
                free_floats[ticker] = self._calculate_free_float(info)
            except Exception as e:
                logger.warning(f"Error fetching free float for {ticker}: {e}")
                free_floats[ticker] = 1.0

        return free_floats

    def get_sector(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch sector classification for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to sector
        """
        yf = self._get_yfinance()
        sectors = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = self._get_stock_info(stock, ticker)
                sectors[ticker] = info.get("sector", "Unknown")
            except Exception as e:
                logger.warning(f"Error fetching sector for {ticker}: {e}")
                sectors[ticker] = "Unknown"

        return sectors

    def get_country(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch country of incorporation for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to country
        """
        yf = self._get_yfinance()
        countries = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = self._get_stock_info(stock, ticker)
                countries[ticker] = info.get("country", "Unknown")
            except Exception as e:
                logger.warning(f"Error fetching country for {ticker}: {e}")
                countries[ticker] = "Unknown"

        return countries

    def get_business_descriptions(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch business descriptions for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to business description
        """
        yf = self._get_yfinance()
        descriptions = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = self._get_stock_info(stock, ticker)
                descriptions[ticker] = info.get("longBusinessSummary", "") or ""
            except Exception as e:
                logger.warning(f"Error fetching description for {ticker}: {e}")
                descriptions[ticker] = ""

        return descriptions

    def is_available(self) -> bool:
        """Check if Yahoo Finance is available."""
        try:
            self._get_yfinance()
            return True
        except ImportError:
            return False

    def get_name(self) -> str:
        """Get connector name."""
        return "Yahoo Finance"

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._price_cache.clear()
        self._info_cache.clear()
