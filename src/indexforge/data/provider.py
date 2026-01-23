"""
Data provider for managing data sources.

The DataProvider abstracts data access and allows switching between
different data sources without changing the index calculation logic.
"""

import logging
from typing import Optional

import pandas as pd

from indexforge.core.constituent import Constituent
from indexforge.data.connectors.base import DataConnector
from indexforge.data.connectors.yahoo import YahooFinanceConnector

logger = logging.getLogger(__name__)


class DataProvider:
    """
    Manages data connectors and provides unified data access.

    The DataProvider allows you to configure one or more data sources
    and provides a unified interface for data access. You can use
    different sources for different types of data.

    This abstraction ensures that the index calculation logic is
    completely decoupled from the data source, making it easy to:
    - Switch from free data to premium data sources
    - Use internal proprietary data
    - Mix different data sources (e.g., prices from one, fundamentals from another)

    Example:
        >>> # Use default Yahoo Finance
        >>> provider = DataProvider.default()
        >>>
        >>> # Use custom data source
        >>> provider = (DataProvider.builder()
        ...     .add_source("prices", my_price_connector)
        ...     .add_source("fundamentals", my_fundamental_connector)
        ...     .set_default("prices")
        ...     .build()
        ... )
    """

    def __init__(
        self,
        connectors: Optional[dict[str, DataConnector]] = None,
        default_connector: Optional[str] = None,
    ) -> None:
        """
        Initialize DataProvider.

        Args:
            connectors: Dictionary of named data connectors
            default_connector: Name of the default connector
        """
        self._connectors: dict[str, DataConnector] = connectors or {}
        self._default_connector: Optional[str] = default_connector

        # Initialize with Yahoo Finance if no connectors provided
        if not self._connectors:
            self._connectors["yahoo"] = YahooFinanceConnector()
            self._default_connector = "yahoo"

    @staticmethod
    def default() -> "DataProvider":
        """
        Create a DataProvider with default Yahoo Finance connector.

        Returns:
            DataProvider configured with Yahoo Finance
        """
        return DataProvider()

    @staticmethod
    def builder() -> "DataProviderBuilder":
        """Create a new DataProviderBuilder."""
        return DataProviderBuilder()

    def get_connector(self, name: Optional[str] = None) -> DataConnector:
        """
        Get a data connector by name.

        Args:
            name: Connector name (uses default if None)

        Returns:
            The requested DataConnector

        Raises:
            KeyError: If connector not found
        """
        if name is None:
            name = self._default_connector

        if name not in self._connectors:
            raise KeyError(f"Data connector '{name}' not found")

        return self._connectors[name]

    def get_prices(
        self, tickers: list[str], start_date: str, end_date: str, source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch historical prices.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source: Data source name (optional)

        Returns:
            DataFrame with price data
        """
        connector = self.get_connector(source)
        return connector.get_prices(tickers, start_date, end_date)

    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None, source: Optional[str] = None
    ) -> list[Constituent]:
        """
        Fetch constituent data.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data
            source: Data source name (optional)

        Returns:
            List of Constituent objects
        """
        connector = self.get_connector(source)
        return connector.get_constituent_data(tickers, as_of_date)

    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None, source: Optional[str] = None
    ) -> dict[str, float]:
        """
        Fetch market capitalization.

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for data
            source: Data source name (optional)

        Returns:
            Dictionary mapping ticker to market cap
        """
        connector = self.get_connector(source)
        return connector.get_market_cap(tickers, as_of_date)

    def get_dividends(
        self, tickers: list[str], start_date: str, end_date: str, source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch dividend data.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            source: Data source name (optional)

        Returns:
            DataFrame with dividend data
        """
        connector = self.get_connector(source)
        return connector.get_dividends(tickers, start_date, end_date)

    def get_splits(
        self, tickers: list[str], start_date: str, end_date: str, source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch stock split data.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            source: Data source name (optional)

        Returns:
            DataFrame with split data
        """
        connector = self.get_connector(source)
        return connector.get_splits(tickers, start_date, end_date)

    def list_connectors(self) -> list[str]:
        """Get list of available connector names."""
        return list(self._connectors.keys())

    def get_default_connector_name(self) -> Optional[str]:
        """Get the name of the default connector."""
        return self._default_connector


class DataProviderBuilder:
    """
    Builder for constructing DataProvider with fluent syntax.

    Example:
        >>> provider = (DataProvider.builder()
        ...     .add_source("yahoo", YahooFinanceConnector())
        ...     .add_source("custom", MyCustomConnector())
        ...     .set_default("yahoo")
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        self._connectors: dict[str, DataConnector] = {}
        self._default_connector: Optional[str] = None

    def add_source(self, name: str, connector: DataConnector) -> "DataProviderBuilder":
        """
        Add a data source connector.

        Args:
            name: Name for this connector
            connector: The DataConnector instance
        """
        self._connectors[name] = connector

        # First connector becomes default
        if self._default_connector is None:
            self._default_connector = name

        return self

    def add_yahoo_finance(self, name: str = "yahoo") -> "DataProviderBuilder":
        """
        Add Yahoo Finance connector.

        Args:
            name: Name for this connector
        """
        return self.add_source(name, YahooFinanceConnector())

    def set_default(self, name: str) -> "DataProviderBuilder":
        """
        Set the default connector.

        Args:
            name: Name of the connector to use as default
        """
        self._default_connector = name
        return self

    def build(self) -> DataProvider:
        """Build the DataProvider object."""
        if not self._connectors:
            # Default to Yahoo Finance
            self._connectors["yahoo"] = YahooFinanceConnector()
            self._default_connector = "yahoo"

        return DataProvider(
            connectors=self._connectors,
            default_connector=self._default_connector,
        )
