"""
Market Data Providers API endpoints.

Allows users to select which data provider to use for market data
(Yahoo Finance, OpenBB, etc.)
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from indexforge import DataSourceError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.crypto import SecretDecryptionError, decrypt_secret, encrypt_secret
from app.db.session import get_db
from app.services.spec_service import DEFAULT_SOURCE

logger = logging.getLogger(__name__)

router = APIRouter()


# Available market data providers (Yahoo Finance is the default)
PROVIDERS: dict[str, dict[str, Any]] = {
    "yahoo": {
        "id": "yahoo",
        "name": "Yahoo Finance",
        "description": "Free market data with a 15 to 20 minute delay. No API key. The default.",
        "features": ["prices", "fundamentals", "dividends", "splits", "stock_screening"],
        "limitations": [
            "Unofficial data feed",
            "Limits bursts of requests, so the first build over a new set of countries "
            "can stop part-way and need a retry",
        ],
        "requires_api_key": False,
        "is_available": True,
        "logo": "https://logo.clearbit.com/yahoo.com",
        "key_url": None,
    },
    "fmp": {
        "id": "fmp",
        "name": "Financial Modeling Prep",
        "description": "Company profiles, sizes and a company screener, with your own API key.",
        "features": ["prices", "fundamentals", "stock_screening"],
        "limitations": [
            "The free plan allows a small number of requests a day and covers few "
            "companies outside the US",
            "Finding companies by rule works only if your plan includes the screener",
        ],
        "requires_api_key": True,
        "is_available": True,
        "logo": "https://site.financialmodelingprep.com/favicon.ico",
        "key_url": "https://site.financialmodelingprep.com/developer/docs",
    },
    "finnhub": {
        "id": "finnhub",
        "name": "Finnhub",
        "description": "Company names, countries, industries and sizes, with your own API key. "
        "For indices that name their companies.",
        "features": ["fundamentals"],
        "limitations": [
            "Cannot find companies by rule, so it only builds indices that list their tickers",
            "No business descriptions, so themes do not work, and no sector rules",
            "Up to 60 requests a minute on the free plan, so builds take about a "
            "second per company",
        ],
        "requires_api_key": True,
        "is_available": True,
        "logo": "https://finnhub.io/favicon.ico",
        "key_url": "https://finnhub.io/register",
    },
    "openbb": {
        "id": "openbb",
        "name": "OpenBB",
        "description": "Open-source financial data platform. For indices that name their companies.",
        "features": ["prices", "fundamentals"],
        "limitations": [
            "Cannot find companies by rule, so it only builds indices that list their tickers",
            "Without paid data keys it reads Yahoo Finance data",
        ],
        "requires_api_key": False,
        "is_available": True,
        "logo": "https://openbb.co/favicon.ico",
        "key_url": None,
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
    # Where to get a key, for providers that need one.
    key_url: Optional[str] = None
    # Whether this user has a key stored. The key itself is never returned.
    has_api_key: bool = False


class ProviderListResponse(BaseModel):
    sources: list[ProviderResponse]
    active_source: str


class SetProviderRequest(BaseModel):
    source_id: str
    api_key: Optional[str] = None


class TestProviderRequest(BaseModel):
    api_key: Optional[str] = None


class ProviderStatusResponse(BaseModel):
    source_id: str
    is_connected: bool
    message: str


def _active_source(user: Any) -> str:
    """The user's saved data source, or the default."""
    source = getattr(user, "market_data_source", None)
    return source if source in PROVIDERS else DEFAULT_SOURCE


def _stored_key(user: Any, provider_id: str) -> str | None:
    """The user's stored API key for a provider, decrypted, or None."""
    stored = (getattr(user, "market_data_keys", None) or {}).get(provider_id)
    try:
        return decrypt_secret(stored)
    except SecretDecryptionError:
        return None


def _provider_response(user: Any, provider_id: str) -> ProviderResponse:
    has_key = bool((getattr(user, "market_data_keys", None) or {}).get(provider_id))
    return ProviderResponse(**PROVIDERS[provider_id], has_api_key=has_key)


@router.get("/", response_model=ProviderListResponse)
async def list_providers(
    current_user: CurrentUser,
) -> ProviderListResponse:
    """
    List all available market data providers.

    Returns the list of supported data providers and which one is currently active.
    """
    return ProviderListResponse(
        sources=[_provider_response(current_user, provider_id) for provider_id in PROVIDERS],
        active_source=_active_source(current_user),
    )


@router.get("/active", response_model=ProviderResponse)
async def get_active_provider(
    current_user: CurrentUser,
) -> ProviderResponse:
    """
    Get the currently active market data provider for the user.
    """
    return _provider_response(current_user, _active_source(current_user))


@router.post("/active", response_model=ProviderStatusResponse)
async def set_active_provider(
    request: SetProviderRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProviderStatusResponse:
    """
    Set the active market data provider for the user.

    A provider that needs an API key uses the one sent with the request, or the
    one already stored for the user. A key that connects is stored encrypted.
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

    new_key = (request.api_key or "").strip() or None
    api_key = new_key or _stored_key(current_user, request.source_id)
    if source["requires_api_key"] and not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{source['name']}' requires an API key.",
        )

    is_connected, message = await run_in_threadpool(_test_provider, request.source_id, api_key)

    if is_connected:
        # Saved on the user, so the background worker that builds indices sees
        # it too. It used to live in this process's memory, where the worker
        # never saw it and a restart forgot it.
        current_user.market_data_source = request.source_id
        if source["requires_api_key"] and new_key:
            # A new dict, so the change to the JSON column is noticed and saved.
            current_user.market_data_keys = {
                **(current_user.market_data_keys or {}),
                request.source_id: encrypt_secret(new_key) or "",
            }
        await db.commit()
        logger.info(f"User {current_user.id} switched to provider: {request.source_id}")

    return ProviderStatusResponse(
        source_id=request.source_id,
        is_connected=is_connected,
        message=message,
    )


@router.post("/{provider_id}/test", response_model=ProviderStatusResponse)
async def test_provider_with_key(
    provider_id: str,
    request: TestProviderRequest,
    current_user: CurrentUser,
) -> ProviderStatusResponse:
    """
    Test connectivity to a market data provider.

    The key travels in the request body, not the address, so it does not end up
    in server logs or browser history. Without one, the stored key is used.
    """
    if provider_id not in PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider_id}",
        )

    api_key = (request.api_key or "").strip() or _stored_key(current_user, provider_id)
    is_connected, message = await run_in_threadpool(_test_provider, provider_id, api_key)
    return ProviderStatusResponse(source_id=provider_id, is_connected=is_connected, message=message)


@router.get("/{provider_id}/test", response_model=ProviderStatusResponse)
async def test_provider(
    provider_id: str,
    current_user: CurrentUser,
) -> ProviderStatusResponse:
    """
    Test connectivity to a market data provider, with the stored key if it needs one.
    """
    return await test_provider_with_key(provider_id, TestProviderRequest(), current_user)


@router.delete("/{provider_id}/key", response_model=ProviderResponse)
async def remove_provider_key(
    provider_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """
    Delete the user's stored API key for a provider.

    If that provider was the active one, the user goes back to the default,
    since it can no longer be used.
    """
    if provider_id not in PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider_id}",
        )

    keys = dict(current_user.market_data_keys or {})
    keys.pop(provider_id, None)
    current_user.market_data_keys = keys or None
    if current_user.market_data_source == provider_id:
        current_user.market_data_source = None
    await db.commit()
    return _provider_response(current_user, provider_id)


def _test_provider(provider_id: str, api_key: Optional[str] = None) -> tuple[bool, str]:
    """Test connectivity to a market data provider. Makes network requests."""
    name = PROVIDERS.get(provider_id, {}).get("name", provider_id)

    if provider_id == "yahoo":
        try:
            from indexforge.data.connectors.yahoo import YahooFinanceConnector

            data = YahooFinanceConnector().get_constituent_data(["AAPL"])
            if data and data[0].market_cap:
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
            return False, "OpenBB is not installed on this server."
        except Exception as e:
            return False, f"OpenBB error: {str(e)}"

    elif provider_id in ("fmp", "finnhub"):
        if not api_key:
            return False, f"{name} requires an API key"
        try:
            # Built without the store: a connection test should reach the provider.
            if provider_id == "fmp":
                from indexforge.data.connectors.fmp import FMPConnector

                connector: Any = FMPConnector(api_key=api_key)
            else:
                from indexforge.data.connectors.finnhub import FinnhubConnector

                connector = FinnhubConnector(api_key=api_key)
            data = connector.get_constituent_data(["AAPL"])
        except DataSourceError as e:
            # Written for the user by the library, and never contains the key.
            return False, str(e)
        except Exception:
            logger.exception("Testing %s failed", name)
            return False, f"{name} could not be reached. Please try again."
        if data and data[0].market_cap:
            return True, f"Successfully connected to {name}"
        return False, f"{name} accepted the key but returned no data for a test company"

    return False, f"Unknown provider: {provider_id}"


def get_user_connector(user_id: str):
    """
    Get the data connector for a user based on their preference.

    Usage:
        connector = get_user_connector(current_user.id)
        data = connector.get_constituent_data(["AAPL", "MSFT"])
    """
    provider_id = "openbb"

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
