"""
Abstract base class for data connectors.

This defines the interface that all data connectors must implement,
allowing for interchangeable data sources.
"""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from indexforge.core.constituent import Constituent


class DataConnector(ABC):
    """
    Abstract base class for data connectors.

    Implement this interface to create connectors for different
    data sources (Yahoo Finance, Bloomberg, Refinitiv, custom data, etc.)

    The data connector provides market data, fundamental data,
    and corporate actions data to the index calculation engine.

    Example:
        >>> class MyCustomConnector(DataConnector):
        ...     def get_prices(self, tickers, start_date, end_date):
        ...         # Your implementation here
        ...         pass
        ...     # ... implement other required methods
    """

    @abstractmethod
    def get_prices(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical prices for given tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            DataFrame with columns for each ticker containing:
            - Open, High, Low, Close, Volume (MultiIndex or flat)
            Index should be DatetimeIndex
        """
        pass

    @abstractmethod
    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> list[Constituent]:
        """
        Fetch constituent data (fundamentals, metadata) for tickers.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data (default: latest available)

        Returns:
            List of Constituent objects with populated data
        """
        pass

    @abstractmethod
    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """
        Fetch market capitalization for tickers.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data (default: latest)

        Returns:
            Dictionary mapping ticker to market cap
        """
        pass

    def get_dividends(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch dividend data for tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with dividend data
        """
        # Default implementation returns empty DataFrame
        return pd.DataFrame()

    def get_splits(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch stock split data for tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with split data
        """
        # Default implementation returns empty DataFrame
        return pd.DataFrame()

    def get_volume(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch trading volume data.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with volume data
        """
        # Can be derived from get_prices in most cases
        prices = self.get_prices(tickers, start_date, end_date)
        if "Volume" in prices.columns:
            return prices["Volume"]
        return pd.DataFrame()

    def get_free_float(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """
        Fetch free float ratio for tickers.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data

        Returns:
            Dictionary mapping ticker to free float ratio (0-1)
        """
        # Default: assume 100% free float
        return {ticker: 1.0 for ticker in tickers}

    def get_sector(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch sector classification for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to sector
        """
        # Default: unknown sector
        return {ticker: "Unknown" for ticker in tickers}

    def get_country(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch country of incorporation for tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to country code
        """
        # Default: unknown country
        return {ticker: "Unknown" for ticker in tickers}

    def get_business_descriptions(self, tickers: list[str]) -> dict[str, str]:
        """
        Fetch business descriptions for tickers.

        This is used for theme-based filtering by keywords.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to business description
        """
        # Default: empty descriptions
        return {ticker: "" for ticker in tickers}

    def is_available(self) -> bool:
        """
        Check if the data connector is available and working.

        Returns:
            True if connector can fetch data
        """
        return True

    def get_name(self) -> str:
        """
        Get the name of this data connector.

        Returns:
            Connector name (e.g., "Yahoo Finance", "Bloomberg")
        """
        return self.__class__.__name__
