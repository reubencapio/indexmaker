"""
API v1 Router

Aggregates all v1 endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    ai,
    auth,
    backtests,
    corporate_actions,
    data_sources,
    delivery,
    embeds,
    indices,
    market_data,
    market_data_providers,
    organizations,
    payments,
    reports,
    support,
    users,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(indices.router, prefix="/indices", tags=["Indices"])
api_router.include_router(backtests.router, prefix="/backtests", tags=["Backtests"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["Market Data"])
api_router.include_router(data_sources.router, prefix="/data-sources", tags=["Data Sources"])
api_router.include_router(
    corporate_actions.router, prefix="/corporate-actions", tags=["Corporate Actions"]
)
api_router.include_router(delivery.router, prefix="/delivery", tags=["Data Delivery"])
api_router.include_router(embeds.router, prefix="/embeds", tags=["Embeds & Shares"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports & Factsheets"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Index Creation"])
api_router.include_router(support.router, prefix="/support", tags=["Support"])
api_router.include_router(
    market_data_providers.router, prefix="/market-data-providers", tags=["Market Data Providers"]
)
api_router.include_router(
    organizations.router, prefix="/organizations", tags=["Organizations & Teams"]
)
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
