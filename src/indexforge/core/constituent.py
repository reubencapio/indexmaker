"""
Constituent model representing a security in an index.

A constituent is a single security that is part of an index's composition.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from indexforge.core.types import Currency


@dataclass
class Constituent:
    """
    Represents a constituent (member) of an index.

    A constituent contains all the information about a security's
    membership in an index, including its weight, shares, and metadata.

    Attributes:
        ticker: The trading symbol (e.g., "AAPL")
        name: Full company name
        weight: Current weight in the index (0.0 to 1.0)
        shares: Number of shares held in the index
        price: Current price per share
        market_cap: Total market capitalization
        free_float_market_cap: Free-float adjusted market cap
        sector: Industry sector
        country: Country of incorporation
        currency: Trading currency
        isin: International Securities Identification Number
        sedol: Stock Exchange Daily Official List number

    Example:
        >>> constituent = Constituent(
        ...     ticker="AAPL",
        ...     name="Apple Inc.",
        ...     weight=0.10,
        ...     shares=1000,
        ...     price=150.0
        ... )
        >>> print(f"{constituent.ticker}: {constituent.weight:.2%}")
        AAPL: 10.00%
    """

    ticker: str
    name: str = ""
    weight: float = 0.0
    shares: float = 0.0
    price: float = 0.0
    market_cap: float = 0.0
    free_float_market_cap: float = 0.0
    free_float_factor: float = 1.0
    sector: str = ""
    industry: str = ""
    country: str = ""
    currency: Currency = Currency.USD
    isin: Optional[str] = None
    sedol: Optional[str] = None
    exchange: str = ""

    # ESG data
    esg_score: Optional[float] = None
    environmental_score: Optional[float] = None
    social_score: Optional[float] = None
    governance_score: Optional[float] = None

    # Fundamental data
    dividend_yield: float = 0.0
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    revenue: float = 0.0
    earnings: float = 0.0

    # Trading data
    average_daily_volume: float = 0.0

    # Metadata
    addition_date: Optional[date] = None
    business_description: str = ""  # Company description for theme filtering

    @property
    def market_value(self) -> float:
        """Calculate market value of position (shares * price)."""
        return self.shares * self.price

    @property
    def identifier(self) -> str:
        """Primary identifier (ticker)."""
        return self.ticker

    def __str__(self) -> str:
        return f"{self.ticker} ({self.name}): {self.weight:.2%}"

    def __repr__(self) -> str:
        return f"Constituent(ticker='{self.ticker}', name='{self.name}', weight={self.weight:.4f})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Constituent):
            return False
        return self.ticker == other.ticker

    def __hash__(self) -> int:
        return hash(self.ticker)

    def to_dict(self) -> dict:
        """Convert constituent to dictionary."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "weight": self.weight,
            "shares": self.shares,
            "price": self.price,
            "market_cap": self.market_cap,
            "sector": self.sector,
            "industry": self.industry,
            "country": self.country,
            "currency": str(self.currency),
            "dividend_yield": self.dividend_yield,
            "average_daily_volume": self.average_daily_volume,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Constituent":
        """Create constituent from dictionary."""
        currency = data.get("currency", "USD")
        if isinstance(currency, str):
            currency = Currency(currency)

        return cls(
            ticker=data["ticker"],
            name=data.get("name", ""),
            weight=data.get("weight", 0.0),
            shares=data.get("shares", 0.0),
            price=data.get("price", 0.0),
            market_cap=data.get("market_cap", 0.0),
            sector=data.get("sector", ""),
            industry=data.get("industry", ""),
            country=data.get("country", ""),
            currency=currency,
            dividend_yield=data.get("dividend_yield", 0.0),
            average_daily_volume=data.get("average_daily_volume", 0.0),
        )
