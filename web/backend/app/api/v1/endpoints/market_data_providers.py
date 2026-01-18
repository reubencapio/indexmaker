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
            from indexmaker.data.connectors.yahoo import YahooFinanceConnector

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

    if provider_id == "openbb":
        try:
            from indexmaker.data.connectors.openbb import OpenBBConnector

            return OpenBBConnector()
        except ImportError:
            # Fall back to Yahoo if OpenBB not installed
            from indexmaker.data.connectors.yahoo import YahooFinanceConnector

            return YahooFinanceConnector()

    elif provider_id == "yahoo":
        from indexmaker.data.connectors.yahoo import YahooFinanceConnector

        return YahooFinanceConnector()

    # Default to OpenBB
    try:
        from indexmaker.data.connectors.openbb import OpenBBConnector

        return OpenBBConnector()
    except ImportError:
        from indexmaker.data.connectors.yahoo import YahooFinanceConnector

        return YahooFinanceConnector()
