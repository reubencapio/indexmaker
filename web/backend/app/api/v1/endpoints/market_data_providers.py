"""
Market Data Providers API endpoints.

Allows users to select which data provider to use for market data
(Yahoo Finance, OpenBB, etc.)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()


# Available market data providers (OpenBB is default)
PROVIDERS = {
    "openbb": {
        "id": "openbb",
        "name": "OpenBB",
        "description": "Open-source financial data platform with stock screening. Default provider.",
        "features": ["prices", "fundamentals", "stock_screening", "index_constituents"],
        "limitations": ["May require additional setup for some data sources"],
        "requires_api_key": False,
        "is_available": True,
        "logo": "https://openbb.co/favicon.ico",
    },
    "yahoo": {
        "id": "yahoo",
        "name": "Yahoo Finance",
        "description": "Free market data with 15-20 min delay. No API key required.",
        "features": ["prices", "fundamentals", "dividends", "splits"],
        "limitations": ["No stock screening", "Delayed data", "Rate limits"],
        "requires_api_key": False,
        "is_available": True,
        "logo": "https://logo.clearbit.com/yahoo.com",
    },
    "fmp": {
        "id": "fmp",
        "name": "Financial Modeling Prep",
        "description": "Free tier with stock screener API. 250 calls/day.",
        "features": ["prices", "fundamentals", "stock_screening", "financials"],
        "limitations": ["250 API calls/day on free tier"],
        "requires_api_key": True,
        "is_available": False,  # Not implemented yet
        "logo": "https://site.financialmodelingprep.com/favicon.ico",
    },
    "polygon": {
        "id": "polygon",
        "name": "Polygon.io",
        "description": "Real-time and historical market data.",
        "features": ["prices", "real_time", "options", "forex"],
        "limitations": ["Limited free tier"],
        "requires_api_key": True,
        "is_available": False,  # Not implemented yet
        "logo": "https://polygon.io/favicon.ico",
    },
}


class ProviderResponse(BaseModel):
    id: str
    name: str
    description: str
    features: list[str]
    limitations: list[str]
    requires_api_key: bool
    is_available: bool
    logo: Optional[str] = None


class ProviderListResponse(BaseModel):
    sources: list[ProviderResponse]
    active_source: str


class SetProviderRequest(BaseModel):
    source_id: str
    api_key: Optional[str] = None


class ProviderStatusResponse(BaseModel):
    source_id: str
    is_connected: bool
    message: str


# In-memory storage for user preferences (in production, store in database)
user_providers: dict[str, str] = {}


@router.get("/", response_model=ProviderListResponse)
async def list_providers(
    current_user: CurrentUser,
) -> ProviderListResponse:
    """
    List all available market data providers.

    Returns the list of supported data providers and which one is currently active.
    """
    sources = [ProviderResponse(**source) for source in PROVIDERS.values()]

    # Get user's active source (default to OpenBB)
    active_source = user_providers.get(str(current_user.id), "openbb")

    return ProviderListResponse(
        sources=sources,
        active_source=active_source,
    )


@router.get("/active", response_model=ProviderResponse)
async def get_active_provider(
    current_user: CurrentUser,
) -> ProviderResponse:
    """
    Get the currently active market data provider for the user.
    """
    source_id = user_providers.get(str(current_user.id), "openbb")
    source = PROVIDERS.get(source_id)

    if not source:
        source = PROVIDERS["openbb"]

    return ProviderResponse(**source)


@router.post("/active", response_model=ProviderStatusResponse)
async def set_active_provider(
    request: SetProviderRequest,
    current_user: CurrentUser,
) -> ProviderStatusResponse:
    """
    Set the active market data provider for the user.

    Some providers require an API key to be provided.
    """
    source = PROVIDERS.get(request.source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {request.source_id}",
        )

    if not source["is_available"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{source['name']}' is not yet available.",
        )

    if source["requires_api_key"] and not request.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{source['name']}' requires an API key.",
        )

    # Test connection
    is_connected, message = await _test_provider(request.source_id, request.api_key)

    if is_connected:
        # Save user preference
        user_providers[str(current_user.id)] = request.source_id
        logger.info(f"User {current_user.id} switched to provider: {request.source_id}")

    return ProviderStatusResponse(
        source_id=request.source_id,
        is_connected=is_connected,
        message=message,
    )


@router.get("/{provider_id}/test", response_model=ProviderStatusResponse)
async def test_provider(
    provider_id: str,
    current_user: CurrentUser,
    api_key: Optional[str] = None,
) -> ProviderStatusResponse:
    """
    Test connectivity to a market data provider.
    """
    source = PROVIDERS.get(provider_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider_id}",
        )

    is_connected, message = await _test_provider(provider_id, api_key)

    return ProviderStatusResponse(
        source_id=provider_id,
        is_connected=is_connected,
        message=message,
    )


async def _test_provider(provider_id: str, api_key: Optional[str] = None) -> tuple[bool, str]:
    """Test connectivity to a market data provider."""

    if provider_id == "yahoo":
        try:
            from indexforge.data.connectors.yahoo import YahooFinanceConnector

            connector = YahooFinanceConnector()
            # Try to get data for a known ticker
            data = connector.get_constituent_data(["AAPL"])
            if data and len(data) > 0:
                return True, "Successfully connected to Yahoo Finance"
            return False, "Yahoo Finance returned no data"
        except Exception as e:
            return False, f"Yahoo Finance error: {str(e)}"

    elif provider_id == "openbb":
        try:
            from openbb import obb

            # Try a simple search
            obb.equity.search("apple", provider="sec")
            return True, "Successfully connected to OpenBB"
        except ImportError:
            return False, "OpenBB is not installed. Run: pip install openbb"
        except Exception as e:
            return False, f"OpenBB error: {str(e)}"

    elif provider_id == "fmp":
        if not api_key:
            return False, "FMP requires an API key"
        # TODO: Implement FMP test
        return False, "FMP connector not yet implemented"

    elif provider_id == "polygon":
        if not api_key:
            return False, "Polygon requires an API key"
        # TODO: Implement Polygon test
        return False, "Polygon connector not yet implemented"

    return False, f"Unknown provider: {provider_id}"


def get_user_connector(user_id: str):
    """
    Get the data connector for a user based on their preference.

    Usage:
        connector = get_user_connector(current_user.id)
        data = connector.get_constituent_data(["AAPL", "MSFT"])
    """
    provider_id = user_providers.get(user_id, "openbb")

    # Use our local OpenBB wrapper instead of indexforge
    return LocalOpenBBConnector(provider=provider_id)


class LocalOpenBBConnector:
    """
    Local OpenBB connector that doesn't depend on indexforge library.
    Used by the web backend for market data fetching.
    """

    #: Constituent fields this connector actually populates. Narrower than the
    #: indexforge connectors: it builds its own lightweight Constituent with no
    #: valuation ratios, dividend yield or free-float data, so factors needing
    #: those cannot be ranked on here. Declared so the capabilities endpoint can
    #: say which factors are usable rather than letting them score every
    #: constituent identically.
    PROVIDES = frozenset(
        {
            "market_cap",
            "average_daily_volume",
            "business_description",
            "sector",
            "industry",
            "country",
        }
    )

    def __init__(self, provider: str = "openbb"):
        self._provider = provider
        self._obb = None

    def _get_openbb(self):
        """Lazy load OpenBB."""
        if self._obb is None:
            try:
                from openbb import obb

                self._obb = obb
            except ImportError:
                raise ImportError("OpenBB is required. Install with: pip install openbb")
        return self._obb

    def get_name(self) -> str:
        return "OpenBB"

    def get_constituent_data(self, tickers: list[str]) -> list:
        """Fetch constituent data, with yfinance fallback if OpenBB fails."""
        from dataclasses import dataclass

        @dataclass
        class Constituent:
            ticker: str
            name: str = ""
            market_cap: float = 0
            sector: str = "Unknown"
            industry: str = "Unknown"
            country: str = "Unknown"
            price: float = 0
            business_description: str = ""
            average_daily_volume: int = 0

        constituents = []

        # Try direct yfinance first (more reliable than OpenBB wrapper)
        try:
            import yfinance as yf

            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info or {}

                    constituent = Constituent(
                        ticker=ticker,
                        name=info.get("shortName", info.get("longName", ticker)),
                        market_cap=info.get("marketCap", 0) or 0,
                        sector=info.get("sector", "Unknown"),
                        industry=info.get("industry", "Unknown"),
                        country=info.get("country", "Unknown"),
                        price=info.get("regularMarketPrice", info.get("currentPrice", 0)) or 0,
                        business_description=info.get("longBusinessSummary", "") or "",
                        average_daily_volume=info.get("averageVolume", 0) or 0,
                    )
                    constituents.append(constituent)

                except Exception as e:
                    logger.warning(f"yfinance error for {ticker}: {e}")
                    constituents.append(Constituent(ticker=ticker, name=ticker))

            return constituents

        except ImportError:
            logger.warning("yfinance not installed, trying OpenBB")

        # Fallback to OpenBB if yfinance not available
        try:
            obb = self._get_openbb()

            for ticker in tickers:
                try:
                    profile = obb.equity.profile(ticker, provider="yfinance")

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

                    constituent = Constituent(
                        ticker=ticker,
                        name=info.get("name", info.get("long_name", ticker)),
                        market_cap=info.get("market_cap", 0) or 0,
                        sector=info.get("sector", "Unknown"),
                        industry=info.get("industry", "Unknown"),
                        country=info.get("country", "Unknown"),
                        price=0,
                        business_description=info.get(
                            "long_business_summary", info.get("description", "")
                        )
                        or "",
                        average_daily_volume=info.get("average_volume", 0) or 0,
                    )
                    constituents.append(constituent)

                except Exception as e:
                    logger.warning(f"OpenBB error for {ticker}: {e}")
                    constituents.append(Constituent(ticker=ticker, name=ticker))

        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            # Return empty constituents with just ticker names
            for ticker in tickers:
                constituents.append(Constituent(ticker=ticker, name=ticker))

        return constituents
