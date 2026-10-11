"""
Plan catalogue: the single definition of what each subscription tier includes.

Limits and feature flags used to be scattered -- a dict on the user model, another
in the data-source endpoint, and marketing copy on two frontend pages that promised
things nothing enforced. Everything that depends on a tier now reads from here, and
the pricing page is rendered from the same data, so what is sold and what is
enforced cannot drift apart.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fastapi import HTTPException, status

FREE = "free"
PRO = "pro"
ENTERPRISE = "enterprise"

# Feature keys. Kept as constants so a typo is an import error, not a silent
# "feature not in plan".
FEATURE_EXTENDED_HISTORY = "extended_history"
FEATURE_DATA_EXPORT = "data_export"
FEATURE_DELIVERY = "delivery"
FEATURE_WHITE_LABEL = "white_label"
FEATURE_AUTO_REFRESH = "auto_refresh"


@dataclass(frozen=True)
class Plan:
    """Limits and features for one tier. None means unlimited."""

    id: str
    name: str
    tagline: str
    max_indices: int | None
    max_data_sources: int | None
    max_public_shares: int | None
    max_embed_widgets: int | None
    # Longest analytics look-back, in years.
    analytics_history_years: int
    features: frozenset[str]
    # Marketing bullets, in display order. Every line here must be true of the
    # limits above -- this is the copy the pricing page shows.
    highlights: tuple[str, ...]

    def has(self, feature: str) -> bool:
        return feature in self.features

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["features"] = sorted(self.features)
        data["highlights"] = list(self.highlights)
        return data


PLANS: dict[str, Plan] = {
    FREE: Plan(
        id=FREE,
        name="Free",
        tagline="Build and test your first indices",
        max_indices=3,
        max_data_sources=2,
        max_public_shares=1,
        max_embed_widgets=1,
        analytics_history_years=1,
        features=frozenset(),
        highlights=(
            "3 custom indices",
            "AI index builder",
            "Backtesting with transaction costs",
            "1 year of performance analytics",
            "1 public share link, with followers",
        ),
    ),
    PRO: Plan(
        id=PRO,
        name="Pro",
        tagline="For investors and advisors who run indices for real",
        max_indices=25,
        max_data_sources=10,
        max_public_shares=None,
        max_embed_widgets=None,
        analytics_history_years=10,
        features=frozenset(
            {
                FEATURE_EXTENDED_HISTORY,
                FEATURE_DATA_EXPORT,
                FEATURE_DELIVERY,
                FEATURE_WHITE_LABEL,
                FEATURE_AUTO_REFRESH,
            }
        ),
        highlights=(
            "25 custom indices",
            "10 years of performance and risk analytics",
            "CSV export of constituents, history and trade lists",
            "Unlimited public share links and embeddable widgets",
            "Remove IndexMaker branding from embeds",
            "Indices recalculated automatically every trading day",
            "Scheduled email reports, and webhooks on every update",
            "10 custom data sources",
            "Priority support",
        ),
    ),
    ENTERPRISE: Plan(
        id=ENTERPRISE,
        name="Enterprise",
        tagline="For institutions and index providers",
        max_indices=1000,
        max_data_sources=None,
        max_public_shares=None,
        max_embed_widgets=None,
        analytics_history_years=30,
        features=frozenset(
            {
                FEATURE_EXTENDED_HISTORY,
                FEATURE_DATA_EXPORT,
                FEATURE_DELIVERY,
                FEATURE_WHITE_LABEL,
                FEATURE_AUTO_REFRESH,
            }
        ),
        highlights=(
            "Everything in Pro",
            "1,000 indices",
            "Unlimited custom data sources",
            "Full price history for analytics",
            "Onboarding and dedicated support",
            "Custom integrations and invoicing",
        ),
    ),
}

FEATURE_LABELS: dict[str, str] = {
    FEATURE_EXTENDED_HISTORY: "Analytics history beyond one year",
    FEATURE_DATA_EXPORT: "CSV data export",
    FEATURE_DELIVERY: "Scheduled reports and webhooks",
    FEATURE_AUTO_REFRESH: "Automatic daily recalculation",
    FEATURE_WHITE_LABEL: "Unbranded embeds",
}


def get_plan(tier: str | None) -> Plan:
    """Plan for a tier, falling back to Free for anything unrecognised."""
    return PLANS.get(tier or FREE, PLANS[FREE])


def upgrade_required(message: str, *, feature: str | None = None, limit: str | None = None):
    """
    Build the error raised when a request needs a higher plan.

    402 rather than 403: the caller is authorised, the plan is what falls short.
    The structured detail lets the client open an upgrade prompt instead of
    showing a dead-end error.
    """
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": "upgrade_required",
            "message": message,
            "feature": feature,
            "limit": limit,
            "required_plan": PRO,
        },
    )


def require_feature(tier: str | None, feature: str) -> None:
    """Raise an upgrade error unless the tier includes `feature`."""
    if not get_plan(tier).has(feature):
        label = FEATURE_LABELS.get(feature, feature)
        raise upgrade_required(f"{label} is available on the Pro plan.", feature=feature)


def require_capacity(tier: str | None, limit_name: str, current: int, noun: str) -> None:
    """Raise an upgrade error if creating one more `noun` would exceed the plan."""
    plan = get_plan(tier)
    limit = getattr(plan, limit_name)
    if limit is not None and current >= limit:
        raise upgrade_required(
            f"Your {plan.name} plan includes {limit} {noun}. Upgrade to add more.",
            limit=limit_name,
        )
