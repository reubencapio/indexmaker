"""
Market data endpoints.

Provides access to market data for index construction.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services.market_data_service import MarketDataService

router = APIRouter()


class SecurityInfo(BaseModel):
    """Security information response."""

    ticker: str
    name: str | None
    sector: str | None
    industry: str | None
    country: str | None
    currency: str | None
    market_cap: float | None
    price: float | None
    avg_volume: float | None
    pe_ratio: float | None
    dividend_yield: float | None


class PriceData(BaseModel):
    """Historical price data."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class SearchResult(BaseModel):
    """Security search result."""

    ticker: str
    name: str
    exchange: str | None
    type: str | None


@router.get("/quote/{ticker}", response_model=SecurityInfo)
async def get_quote(
    current_user: CurrentUser,
    ticker: str,
) -> SecurityInfo:
    """
    Get current quote and info for a security.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Security information and current price
    """
    service = MarketDataService()
    data = await service.get_security_info(ticker)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {ticker} not found",
        )

    return SecurityInfo(**data)


@router.get("/quotes", response_model=list[SecurityInfo])
async def get_quotes(
    current_user: CurrentUser,
    tickers: str = Query(..., description="Comma-separated list of tickers"),
) -> list[SecurityInfo]:
    """
    Get quotes for multiple securities.

    Args:
        tickers: Comma-separated ticker symbols (e.g., "AAPL,MSFT,GOOGL")

    Returns:
        List of security information
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    if len(ticker_list) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 tickers per request",
        )

    service = MarketDataService()
    results = []

    for ticker in ticker_list:
        data = await service.get_security_info(ticker)
        if data:
            results.append(SecurityInfo(**data))

    return results


@router.get("/history/{ticker}", response_model=list[PriceData])
async def get_price_history(
    current_user: CurrentUser,
    ticker: str,
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
) -> list[PriceData]:
    """
    Get historical price data for a security.

    Args:
        ticker: Stock ticker symbol
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of daily OHLCV data
    """
    service = MarketDataService()
    data = await service.get_price_history(ticker, start_date, end_date)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data found for {ticker}",
        )

    return [PriceData(**row) for row in data]


@router.get("/search", response_model=list[SearchResult])
async def search_securities(
    current_user: CurrentUser,
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[SearchResult]:
    """
    Search for securities by name or ticker.

    Args:
        query: Search term (ticker or company name)
        limit: Maximum results

    Returns:
        List of matching securities
    """
    service = MarketDataService()
    results = await service.search_securities(query, limit)
    return [SearchResult(**r) for r in results]


@router.get("/sectors")
async def get_sectors(
    current_user: CurrentUser,
) -> list[str]:
    """Get list of available sectors for filtering."""
    return [
        "Communication Services",
        "Consumer Discretionary",
        "Consumer Staples",
        "Energy",
        "Financials",
        "Health Care",
        "Industrials",
        "Information Technology",
        "Materials",
        "Real Estate",
        "Utilities",
    ]


@router.get("/countries")
async def get_countries(
    current_user: CurrentUser,
) -> list[dict[str, str]]:
    """Get list of available countries for filtering."""
    return [
        {"code": "US", "name": "United States"},
        {"code": "CA", "name": "Canada"},
        {"code": "GB", "name": "United Kingdom"},
        {"code": "DE", "name": "Germany"},
        {"code": "FR", "name": "France"},
        {"code": "JP", "name": "Japan"},
        {"code": "CN", "name": "China"},
        {"code": "HK", "name": "Hong Kong"},
        {"code": "AU", "name": "Australia"},
        {"code": "CH", "name": "Switzerland"},
        {"code": "NL", "name": "Netherlands"},
        {"code": "KR", "name": "South Korea"},
        {"code": "TW", "name": "Taiwan"},
        {"code": "IN", "name": "India"},
        {"code": "BR", "name": "Brazil"},
    ]

