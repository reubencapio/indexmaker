"""Pytest configuration and fixtures."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from indexforge.core.constituent import Constituent
from indexforge.core.index import Index
from indexforge.core.types import Currency
from indexforge.core.universe import Universe
from indexforge.data.connectors.base import DataConnector


class MockDataConnector(DataConnector):
    """Mock data connector for testing without real API calls."""

    def __init__(self, constituents=None, prices=None):
        self._constituents = constituents or []
        self._prices = prices

    def get_prices(self, tickers, start_date, end_date):
        if self._prices is not None:
            return self._prices

        # Generate mock price data
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        data = {}
        for ticker in tickers:
            base_price = 100 + hash(ticker) % 100
            prices = base_price * (1 + np.random.randn(len(dates)) * 0.02).cumprod()
            data[(ticker, "Open")] = prices * 0.99
            data[(ticker, "High")] = prices * 1.01
            data[(ticker, "Low")] = prices * 0.98
            data[(ticker, "Close")] = prices
            data[(ticker, "Volume")] = np.random.randint(1000000, 10000000, len(dates))

        df = pd.DataFrame(data, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)
        return df

    def get_constituent_data(self, tickers, as_of_date=None):
        if self._constituents:
            return [c for c in self._constituents if c.ticker in tickers]

        # Generate mock constituent data
        return [
            Constituent(
                ticker=ticker,
                name=f"Company {ticker}",
                market_cap=1e12 * (1 + hash(ticker) % 5),
                sector="Technology",
                country="US",
                price=100 + hash(ticker) % 100,
                dividend_yield=0.01 + (hash(ticker) % 10) / 100,
                average_daily_volume=1e7,
            )
            for ticker in tickers
        ]

    def get_market_cap(self, tickers, as_of_date=None):
        constituents = self.get_constituent_data(tickers, as_of_date)
        return {c.ticker: c.market_cap for c in constituents}

    def get_name(self):
        return "Mock Data Connector"


@pytest.fixture
def mock_connector():
    """Provide a mock data connector."""
    return MockDataConnector()


@pytest.fixture
def sample_constituents():
    """Provide sample constituents for testing."""
    return [
        Constituent(
            ticker="AAPL",
            name="Apple Inc.",
            market_cap=3e12,
            sector="Technology",
            country="US",
            price=175.0,
            dividend_yield=0.005,
            average_daily_volume=5e7,
        ),
        Constituent(
            ticker="MSFT",
            name="Microsoft Corporation",
            market_cap=2.5e12,
            sector="Technology",
            country="US",
            price=350.0,
            dividend_yield=0.008,
            average_daily_volume=3e7,
        ),
        Constituent(
            ticker="GOOGL",
            name="Alphabet Inc.",
            market_cap=1.5e12,
            sector="Communication Services",
            country="US",
            price=140.0,
            dividend_yield=0.0,
            average_daily_volume=2e7,
        ),
        Constituent(
            ticker="AMZN",
            name="Amazon.com Inc.",
            market_cap=1.4e12,
            sector="Consumer Discretionary",
            country="US",
            price=150.0,
            dividend_yield=0.0,
            average_daily_volume=4e7,
        ),
        Constituent(
            ticker="JPM",
            name="JPMorgan Chase & Co.",
            market_cap=0.5e12,
            sector="Financials",
            country="US",
            price=180.0,
            dividend_yield=0.025,
            average_daily_volume=1e7,
        ),
    ]


@pytest.fixture
def sample_universe():
    """Provide a sample universe for testing."""
    return Universe.from_tickers(["AAPL", "MSFT", "GOOGL", "AMZN", "JPM"])


@pytest.fixture
def sample_index(sample_universe, mock_connector):
    """Provide a sample index for testing."""
    from indexforge.data.provider import DataProvider

    provider = DataProvider.builder().add_source("mock", mock_connector).build()

    index = Index.create(
        name="Test Index",
        identifier="TEST",
        currency=Currency.USD,
        base_date="2024-01-01",
        base_value=1000.0,
    )
    index.set_universe(sample_universe)
    index.set_data_provider(provider)

    return index


@pytest.fixture
def mock_yfinance():
    """Mock yfinance for testing."""
    with patch("indexforge.data.connectors.yahoo.yf") as mock:
        # Setup mock ticker
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "marketCap": 3e12,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "United States",
            "currency": "USD",
            "dividendYield": 0.005,
            "sharesOutstanding": 15e9,
            "floatShares": 14e9,
        }
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Close": [175.0],
            },
            index=pd.DatetimeIndex([datetime.now()]),
        )

        mock.Ticker.return_value = mock_ticker

        # Setup mock download
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        mock_data = pd.DataFrame(
            {
                ("AAPL", "Close"): np.linspace(170, 180, 100),
                ("AAPL", "Open"): np.linspace(169, 179, 100),
                ("AAPL", "High"): np.linspace(172, 182, 100),
                ("AAPL", "Low"): np.linspace(168, 178, 100),
                ("AAPL", "Volume"): [1e7] * 100,
            },
            index=dates,
        )
        mock_data.columns = pd.MultiIndex.from_tuples(mock_data.columns)
        mock.download.return_value = mock_data

        yield mock
