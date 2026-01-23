#!/usr/bin/env python3
"""
Data Source Configuration Examples

This example shows how to configure different data sources:
1. Default Yahoo Finance (free)
2. Custom database (PostgreSQL, MySQL, etc.)
3. Bloomberg/Refinitiv API
4. CSV files
5. Multiple sources combined

The key principle: Your index logic stays the same,
only the data source changes.
"""

from typing import Optional

import pandas as pd

from indexforge import (
    Constituent,
    Currency,
    DataConnector,
    DataProvider,
    Index,
    Universe,
    WeightingMethod,
    YahooFinanceConnector,
)

# =============================================================================
# EXAMPLE 1: Default Yahoo Finance (No configuration needed)
# =============================================================================


def example_default_yahoo():
    """Use Yahoo Finance - the default, no configuration needed."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Default Yahoo Finance")
    print("=" * 60)

    # Just create the index - Yahoo Finance is used by default
    index = Index.create(
        name="Simple Index",
        identifier="SIMPLE",
        currency=Currency.USD,
        base_date="2024-01-01",
        base_value=1000.0,
    )

    index.set_universe(Universe.from_tickers(["AAPL", "MSFT", "GOOGL"]))
    index.set_weighting_method(WeightingMethod.equal_weight())

    print("✅ Using default Yahoo Finance - no configuration needed!")
    print(f"   Index: {index.name}")


# =============================================================================
# EXAMPLE 2: Custom Database Connector
# =============================================================================


class PostgreSQLConnector(DataConnector):
    """
    Example: Connect to a PostgreSQL database.

    Replace the SQL queries with your actual table structure.
    """

    def __init__(self, connection_string: str):
        """
        Initialize database connection.

        Args:
            connection_string: e.g., "postgresql://user:pass@localhost/mydb"
        """
        self.connection_string = connection_string
        self._engine = None
        print("   📦 PostgreSQL connector initialized")

    def _get_engine(self):
        """Lazy load database engine."""
        if self._engine is None:
            # In production, uncomment:
            # from sqlalchemy import create_engine
            # self._engine = create_engine(self.connection_string)
            pass
        return self._engine

    def get_prices(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch prices from your database.

        Expected table structure:
            daily_prices (date, ticker, open, high, low, close, volume)
        """
        # In production:
        # df = pd.read_sql(query, self._get_engine(), params={
        #     'tickers': tickers,
        #     'start': start_date,
        #     'end': end_date
        # })
        # return self._pivot_to_multi_index(df)

        # For demo, return empty DataFrame
        print(f"   Would query: {len(tickers)} tickers from {start_date} to {end_date}")
        return pd.DataFrame()

    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> list[Constituent]:
        """
        Fetch constituent data from your database.

        Expected table structure:
            companies (ticker, name, market_cap, sector, industry, country)
        """
        # In production:
        # df = pd.read_sql(query, self._get_engine(), params={'tickers': tickers})
        # return [
        #     Constituent(
        #         ticker=row['ticker'],
        #         name=row['name'],
        #         market_cap=row['market_cap'],
        #         sector=row['sector'],
        #         country=row['country'],
        #     )
        #     for _, row in df.iterrows()
        # ]

        print(f"   Would fetch constituent data for: {tickers}")
        return [Constituent(ticker=t, name=f"Company {t}") for t in tickers]

    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """Fetch market caps from database."""
        # In production: query your market_cap table
        return {t: 1e12 for t in tickers}

    def get_name(self) -> str:
        return "PostgreSQL Database"


def example_database():
    """Use a custom database as data source."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Custom Database (PostgreSQL)")
    print("=" * 60)

    # Create your database connector
    db_connector = PostgreSQLConnector(
        connection_string="postgresql://user:password@localhost:5432/market_data"
    )

    # Create data provider with your connector
    provider = (
        DataProvider.builder().add_source("database", db_connector).set_default("database").build()
    )

    # Create index with custom data provider
    index = Index.create(
        name="Database Index",
        identifier="DBIDX",
        currency=Currency.USD,
        base_date="2024-01-01",
        base_value=1000.0,
    )

    index.set_universe(Universe.from_tickers(["AAPL", "MSFT"]))
    index.set_weighting_method(WeightingMethod.market_cap().build())
    index.set_data_provider(provider)  # Use custom data!

    print(f"✅ Using database: {provider.get_connector().get_name()}")


# =============================================================================
# EXAMPLE 3: Bloomberg API Connector
# =============================================================================


class BloombergConnector(DataConnector):
    """
    Example: Connect to Bloomberg API.

    This is a template - replace with actual Bloomberg API calls.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        # In production: self.client = BloombergClient(api_key)
        print("   📊 Bloomberg connector initialized")

    def get_prices(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch prices from Bloomberg API."""
        # In production:
        # response = self.client.get_historical_data(
        #     securities=tickers,
        #     fields=['PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'VOLUME'],
        #     start_date=start_date,
        #     end_date=end_date
        # )
        # return self._convert_to_dataframe(response)

        print(f"   Would call Bloomberg API for {tickers}")
        return pd.DataFrame()

    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> list[Constituent]:
        """Fetch constituent data from Bloomberg."""
        # In production:
        # response = self.client.get_reference_data(
        #     securities=tickers,
        #     fields=['NAME', 'CUR_MKT_CAP', 'GICS_SECTOR_NAME', 'COUNTRY']
        # )

        print(f"   Would fetch Bloomberg reference data for {tickers}")
        return [Constituent(ticker=t, name=f"Company {t}") for t in tickers]

    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """Fetch market caps from Bloomberg."""
        return {t: 1e12 for t in tickers}

    def get_name(self) -> str:
        return "Bloomberg"


def example_bloomberg():
    """Use Bloomberg as data source."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Bloomberg API")
    print("=" * 60)

    provider = (
        DataProvider.builder()
        .add_source("bloomberg", BloombergConnector(api_key="your-api-key"))
        .set_default("bloomberg")
        .build()
    )

    index = Index.create(
        name="Bloomberg Index",
        identifier="BBGIDX",
        currency=Currency.USD,
        base_date="2024-01-01",
        base_value=1000.0,
    )

    index.set_data_provider(provider)
    print(f"✅ Using: {provider.get_connector().get_name()}")


# =============================================================================
# EXAMPLE 4: CSV File Connector
# =============================================================================


class CSVConnector(DataConnector):
    """
    Example: Read data from CSV files.

    Useful for backtesting with historical data files.
    """

    def __init__(self, prices_file: str, fundamentals_file: str):
        self.prices_file = prices_file
        self.fundamentals_file = fundamentals_file
        print(f"   📁 CSV connector: {prices_file}")

    def get_prices(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Load prices from CSV."""
        # df = pd.read_csv(self.prices_file, parse_dates=['date'], index_col='date')
        # filtered = df[(df.index >= start_date) & (df.index <= end_date)]
        # return filtered[tickers]

        print(f"   Would load prices from {self.prices_file}")
        return pd.DataFrame()

    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> list[Constituent]:
        """Load fundamentals from CSV."""
        # df = pd.read_csv(self.fundamentals_file)
        # return [Constituent(**row) for _, row in df[df['ticker'].isin(tickers)].iterrows()]

        print(f"   Would load fundamentals from {self.fundamentals_file}")
        return [Constituent(ticker=t) for t in tickers]

    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        return {t: 1e12 for t in tickers}

    def get_name(self) -> str:
        return "CSV Files"


def example_csv():
    """Use CSV files as data source."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: CSV Files")
    print("=" * 60)

    provider = (
        DataProvider.builder()
        .add_source(
            "csv",
            CSVConnector(
                prices_file="data/historical_prices.csv",
                fundamentals_file="data/company_fundamentals.csv",
            ),
        )
        .build()
    )

    print(f"✅ Using: {provider.get_connector().get_name()}")


# =============================================================================
# EXAMPLE 5: Multiple Data Sources Combined
# =============================================================================


def example_multiple_sources():
    """Use different sources for different data types."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Multiple Data Sources")
    print("=" * 60)

    # You can add multiple sources and choose which to use
    provider = (
        DataProvider.builder()
        .add_source("yahoo", YahooFinanceConnector())  # Free prices
        .add_source("internal", PostgreSQLConnector("..."))  # Internal fundamentals
        .add_source("bloomberg", BloombergConnector("..."))  # Premium data
        .set_default("yahoo")
        .build()
    )

    print(f"✅ Available sources: {provider.list_connectors()}")
    print(f"   Default: {provider.get_default_connector_name()}")

    # Use different sources for different calls
    # prices = provider.get_prices(tickers, start, end, source="yahoo")
    # fundamentals = provider.get_constituent_data(tickers, source="internal")


# =============================================================================
# EXAMPLE 6: Environment-Based Configuration
# =============================================================================


def example_environment_config():
    """Configure data source based on environment."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Environment-Based Configuration")
    print("=" * 60)

    import os

    # Read from environment variable
    env = os.getenv("INDEX_ENV", "development")

    if env == "production":
        # Production: use Bloomberg
        connector = BloombergConnector(api_key=os.getenv("BLOOMBERG_API_KEY", ""))
        source_name = "bloomberg"
    elif env == "staging":
        # Staging: use internal database
        connector = PostgreSQLConnector(os.getenv("DATABASE_URL", ""))
        source_name = "database"
    else:
        # Development: use free Yahoo Finance
        connector = YahooFinanceConnector()
        source_name = "yahoo"

    provider = DataProvider.builder().add_source(source_name, connector).build()

    print(f"✅ Environment: {env}")
    print(f"   Using: {provider.get_connector().get_name()}")


# =============================================================================
# SUMMARY
# =============================================================================


def print_summary():
    """Print summary of data source configuration."""
    print("\n" + "=" * 60)
    print("SUMMARY: HOW TO CONFIGURE DATA SOURCES")
    print("=" * 60)
    print(
        """
1. DEFAULT (Yahoo Finance):
   index = Index.create(...)  # Just works!

2. CUSTOM DATABASE:
   class MyDBConnector(DataConnector):
       def get_prices(...): ...
       def get_constituent_data(...): ...
       def get_market_cap(...): ...

   provider = DataProvider.builder().add_source("db", MyDBConnector()).build()
   index.set_data_provider(provider)

3. BLOOMBERG/REFINITIV:
   provider = DataProvider.builder().add_source("bbg", BloombergConnector()).build()
   index.set_data_provider(provider)

4. CSV FILES:
   provider = DataProvider.builder().add_source("csv", CSVConnector()).build()
   index.set_data_provider(provider)

5. MULTIPLE SOURCES:
   provider = (DataProvider.builder()
       .add_source("yahoo", YahooFinanceConnector())
       .add_source("internal", MyDBConnector())
       .set_default("yahoo")
       .build()
   )

KEY PRINCIPLE:
   Your index logic stays EXACTLY the same.
   Only the data source configuration changes.
   Swap Yahoo → Bloomberg → Database with one line change!
    """
    )


if __name__ == "__main__":
    example_default_yahoo()
    example_database()
    example_bloomberg()
    example_csv()
    example_multiple_sources()
    example_environment_config()
    print_summary()
