#!/usr/bin/env python3
"""
Custom Data Source Example

This example shows how to create an index using your own data source
by implementing a custom DataConnector.

This pattern allows you to:
- Use proprietary data from your company's databases
- Connect to alternative data providers (Bloomberg, Refinitiv, etc.)
- Use CSV files or databases as data sources
- Mix multiple data sources

Run with: python examples/custom_data_source.py
"""

from typing import Optional

import numpy as np
import pandas as pd

from indexmaker import (
    AssetClass,
    Constituent,
    Currency,
    DataConnector,
    DataProvider,
    Index,
    Universe,
    WeightingMethod,
)


class CSVDataConnector(DataConnector):
    """
    Example custom data connector that reads from CSV files.

    Replace this with your own data source logic:
    - Database connection
    - API calls to your data vendor
    - Internal data warehouse queries
    """

    def __init__(self, prices_file: str = None, fundamentals_file: str = None):
        """
        Initialize the connector.

        Args:
            prices_file: Path to CSV with price data
            fundamentals_file: Path to CSV with fundamental data
        """
        self.prices_file = prices_file
        self.fundamentals_file = fundamentals_file

        # For this example, we'll use generated data
        # In production, load from your files or database
        self._mock_data = self._generate_mock_data()

    def _generate_mock_data(self) -> dict:
        """Generate mock data for demonstration."""
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

        # Mock fundamental data
        fundamentals = {
            "AAPL": {"name": "Apple Inc.", "market_cap": 3e12, "sector": "Technology"},
            "MSFT": {"name": "Microsoft Corp.", "market_cap": 2.5e12, "sector": "Technology"},
            "GOOGL": {"name": "Alphabet Inc.", "market_cap": 1.5e12, "sector": "Communication"},
            "AMZN": {"name": "Amazon.com Inc.", "market_cap": 1.4e12, "sector": "Consumer"},
            "META": {"name": "Meta Platforms", "market_cap": 1e12, "sector": "Technology"},
        }

        # Mock price data
        dates = pd.date_range("2024-01-01", "2024-11-15", freq="D")
        prices = {}
        for ticker in tickers:
            base = 100 + hash(ticker) % 100
            prices[ticker] = base * (1 + np.random.randn(len(dates)) * 0.01).cumprod()

        return {
            "fundamentals": fundamentals,
            "prices": pd.DataFrame(prices, index=dates),
        }

    def get_prices(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch price data from your custom source.

        Replace this with your actual data fetching logic.
        """
        # Filter by date range
        prices = self._mock_data["prices"]
        mask = (prices.index >= start_date) & (prices.index <= end_date)
        filtered = prices.loc[mask, [t for t in tickers if t in prices.columns]]

        # Convert to expected format with MultiIndex columns
        data = {}
        for ticker in filtered.columns:
            data[(ticker, "Open")] = filtered[ticker] * 0.99
            data[(ticker, "High")] = filtered[ticker] * 1.01
            data[(ticker, "Low")] = filtered[ticker] * 0.98
            data[(ticker, "Close")] = filtered[ticker]
            data[(ticker, "Volume")] = [1e6] * len(filtered)

        result = pd.DataFrame(data, index=filtered.index)
        result.columns = pd.MultiIndex.from_tuples(result.columns)
        return result

    def get_constituent_data(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> list[Constituent]:
        """
        Fetch constituent data from your custom source.

        Replace this with your actual data fetching logic.
        """
        constituents = []

        for ticker in tickers:
            if ticker in self._mock_data["fundamentals"]:
                data = self._mock_data["fundamentals"][ticker]

                # Get latest price
                if ticker in self._mock_data["prices"].columns:
                    price = self._mock_data["prices"][ticker].iloc[-1]
                else:
                    price = 100.0

                constituent = Constituent(
                    ticker=ticker,
                    name=data["name"],
                    market_cap=data["market_cap"],
                    sector=data["sector"],
                    country="US",
                    currency=Currency.USD,
                    price=price,
                )
                constituents.append(constituent)

        return constituents

    def get_market_cap(
        self, tickers: list[str], as_of_date: Optional[str] = None
    ) -> dict[str, float]:
        """Get market cap from your custom source."""
        result = {}
        for ticker in tickers:
            if ticker in self._mock_data["fundamentals"]:
                result[ticker] = self._mock_data["fundamentals"][ticker]["market_cap"]
        return result

    def get_name(self) -> str:
        return "Custom CSV Data Connector"


class DatabaseConnector(DataConnector):
    """
    Example database connector.

    This shows how you might connect to a SQL database.
    Customize for your specific database (PostgreSQL, MySQL, etc.)
    """

    def __init__(self, connection_string: str):
        """
        Initialize database connection.

        Args:
            connection_string: Database connection string
        """
        self.connection_string = connection_string
        # In production: self.engine = create_engine(connection_string)
        print(f"📦 Database connector initialized (connection: {connection_string})")

    def get_prices(self, tickers, start_date, end_date):
        """
        Example SQL query for prices.

        Replace with your actual database query.
        """
        # Example query:
        # query = '''
        #     SELECT date, ticker, open, high, low, close, volume
        #     FROM daily_prices
        #     WHERE ticker IN %(tickers)s
        #     AND date BETWEEN %(start)s AND %(end)s
        #     ORDER BY date
        # '''
        # return pd.read_sql(query, self.engine, params={...})

        # For demo, return empty DataFrame
        return pd.DataFrame()

    def get_constituent_data(self, tickers, as_of_date=None):
        """
        Example SQL query for fundamentals.

        Replace with your actual database query.
        """
        # Example query:
        # query = '''
        #     SELECT ticker, name, market_cap, sector, country
        #     FROM company_fundamentals
        #     WHERE ticker IN %(tickers)s
        #     AND date = %(as_of_date)s
        # '''
        # df = pd.read_sql(query, self.engine, params={...})
        # return [Constituent(**row) for row in df.to_dict('records')]

        return []

    def get_market_cap(self, tickers, as_of_date=None):
        return {t: 0 for t in tickers}

    def get_name(self):
        return "Custom Database Connector"


def main():
    """Demonstrate using custom data sources."""

    print("=" * 60)
    print("Custom Data Source Example")
    print("=" * 60)
    print()

    # Create custom data connector
    print("1. Creating custom data connector...")
    custom_connector = CSVDataConnector()
    print(f"   ✅ Created: {custom_connector.get_name()}")

    # Create data provider with custom connector
    print("\n2. Configuring data provider...")
    data_provider = (
        DataProvider.builder().add_source("custom", custom_connector).set_default("custom").build()
    )
    print(f"   ✅ Available sources: {data_provider.list_connectors()}")
    print(f"   ✅ Default source: {data_provider.get_default_connector_name()}")

    # Create index
    print("\n3. Creating index...")
    index = Index.create(
        name="Custom Data Index",
        identifier="CUSTOM",
        currency=Currency.USD,
        base_date="2024-01-01",
        base_value=1000.0,
    )

    # Configure with custom data provider
    # universe = Universe.from_tickers(["AAPL", "MSFT", "GOOGL", "AMZN", "META"])
    universe = (
        Universe.builder()
        .asset_class(AssetClass.EQUITIES)
        .tickers(["AAPL", "MSFT", "GOOGL", "AMZN", "META"])
        .build()
    )

    (
        index.set_universe(universe)
        .set_weighting_method(WeightingMethod.equal_weight())
        .set_data_provider(data_provider)  # Use custom data!
    )
    print("   ✅ Index configured with custom data source")

    # Fetch data using custom connector
    print("\n4. Fetching constituent data...")
    constituents = data_provider.get_constituent_data(universe.tickers, source="custom")

    print(f"   📊 Retrieved {len(constituents)} constituents:")
    for c in constituents:
        print(f"      {c.ticker}: {c.name} - ${c.market_cap/1e9:.0f}B")

    # Fetch prices
    print("\n5. Fetching price data...")
    prices = data_provider.get_prices(universe.tickers, "2024-01-01", "2024-11-15", source="custom")
    print(
        f"   📈 Retrieved {len(prices)} days of prices for {len(prices.columns.levels[0])} tickers"
    )

    print()
    print("=" * 60)
    print("KEY TAKEAWAYS")
    print("=" * 60)
    print(
        """
To use your own data source:

1. Create a class that inherits from DataConnector
2. Implement required methods:
   - get_prices(tickers, start_date, end_date)
   - get_constituent_data(tickers, as_of_date)
   - get_market_cap(tickers, as_of_date)

3. Create a DataProvider with your connector:
   provider = DataProvider.builder()
       .add_source("mydata", MyConnector())
       .build()

4. Use it in your index:
   index.set_data_provider(provider)

Benefits:
- Complete control over data source
- Can use proprietary data
- Can mix multiple data sources
- API remains the same regardless of data source
    """
    )


if __name__ == "__main__":
    main()
