"""
Capability reporting.

Tells the client which ranking factors this deployment can actually compute, and
which are blocked by the caller's active data source. The UI uses this to stop
offering factors that would silently score every constituent the same -- which is
what used to happen, with no error anywhere.

The factor registry in indexforge is the single source of truth; nothing here
maintains a second list.
"""

from fastapi import APIRouter
from indexforge.core.types import Factor
from indexforge.selection.factors import (
    FACTOR_REGISTRY,
    UNSUPPORTED_FACTORS,
    missing_requirements,
)
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.api.v1.endpoints.market_data_providers import get_user_connector

router = APIRouter()


class FactorCapability(BaseModel):
    """Whether one factor can be used, and if not, why not."""

    factor: str
    available: bool
    higher_is_better: bool | None = None
    # Populated when the factor is implemented but the active data source does not
    # supply what it needs -- a different problem from it not being implemented,
    # and one the user can fix by switching provider.
    missing_fields: list[str] = []
    reason: str | None = None


class CapabilitiesResponse(BaseModel):
    """Ranking factors available to the caller right now."""

    data_source: str
    factors: list[FactorCapability]


@router.get("", response_model=CapabilitiesResponse)
async def get_capabilities(current_user: CurrentUser) -> CapabilitiesResponse:
    """
    Report which ranking factors are usable with the caller's data source.

    Unimplemented factors are listed as unavailable rather than omitted, so the UI
    can show them greyed out with a reason instead of leaving users to guess why a
    factor they expected is missing.
    """
    connector = get_user_connector(str(current_user.id))
    provided = getattr(connector, "PROVIDES", frozenset())

    factors: list[FactorCapability] = []

    for factor, spec in sorted(FACTOR_REGISTRY.items(), key=lambda kv: kv[0].name):
        missing = missing_requirements(factor, provided)
        factors.append(
            FactorCapability(
                factor=factor.name,
                available=not missing,
                higher_is_better=spec.higher_is_better,
                missing_fields=list(missing),
                reason=(
                    None
                    if not missing
                    else f"Not provided by {connector.get_name()}: {', '.join(missing)}"
                ),
            )
        )

    for factor in sorted(UNSUPPORTED_FACTORS, key=lambda f: f.name):
        factors.append(
            FactorCapability(
                factor=factor.name,
                available=False,
                reason="Not yet implemented",
            )
        )

    return CapabilitiesResponse(
        data_source=connector.get_name(),
        factors=factors,
    )


@router.get("/factors", response_model=list[str])
async def list_supported_factors() -> list[str]:
    """
    Factors this build can compute, ignoring any particular data source.

    Unauthenticated so tooling and the code generator can check the contract
    without credentials.
    """
    return sorted(f.name for f in Factor if f in FACTOR_REGISTRY)
