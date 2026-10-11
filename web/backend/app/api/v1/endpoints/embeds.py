"""
Embeddable Widgets and Public Shares API endpoints.
"""

import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.core.plans import FEATURE_WHITE_LABEL, get_plan, require_capacity, require_feature
from app.core.security import get_password_hash, verify_password
from app.models.embed import EmbedWidget, PublicShare
from app.models.index import Index
from app.schemas.embed import (
    EmbedWidgetCreate,
    EmbedWidgetResponse,
    EmbedWidgetUpdate,
    PublicShareCreate,
    PublicShareResponse,
    PublicShareUpdate,
)
from app.services import analytics_service, follower_service
from app.services.analytics_service import PERIOD_YEARS, AnalyticsUnavailableError

router = APIRouter()


def generate_slug() -> str:
    """Generate a random URL-safe slug."""
    return secrets.token_urlsafe(8).lower().replace("_", "-")[:12]


def generate_embed_token() -> str:
    """Generate a secure embed token."""
    return secrets.token_urlsafe(32)


# ============== PUBLIC SHARES ==============


@router.get("/shares", response_model=list[PublicShareResponse])
async def list_public_shares(
    db: DBSession,
    current_user: CurrentUser,
) -> list[PublicShare]:
    """List all public shares for the current user."""
    result = await db.execute(
        select(PublicShare)
        .where(PublicShare.owner_id == current_user.id)
        .order_by(PublicShare.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/shares", response_model=PublicShareResponse, status_code=status.HTTP_201_CREATED)
async def create_public_share(
    db: DBSession,
    current_user: CurrentUser,
    share_in: PublicShareCreate,
    request: Request,
) -> PublicShare:
    """Create a new public share link for an index."""
    # Verify index ownership
    result = await db.execute(select(Index).where(Index.id == share_in.index_id))
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    if index.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    share_count = await db.scalar(
        select(func.count(PublicShare.id)).where(PublicShare.owner_id == current_user.id)
    )
    require_capacity(current_user.tier, "max_public_shares", share_count or 0, "public share link")

    # Generate or validate slug
    slug = share_in.slug or generate_slug()

    # Check slug uniqueness
    result = await db.execute(select(PublicShare).where(PublicShare.slug == slug))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="This slug is already taken. Please choose another."
        )

    # Hash password if provided
    password_hash = None
    if share_in.password:
        password_hash = get_password_hash(share_in.password)

    share = PublicShare(
        index_id=share_in.index_id,
        owner_id=current_user.id,
        slug=slug,
        show_chart=share_in.show_chart,
        show_components=share_in.show_components,
        show_performance=share_in.show_performance,
        show_factsheet=share_in.show_factsheet,
        allow_download=share_in.allow_download,
        title_override=share_in.title_override,
        description_override=share_in.description_override,
        theme=share_in.theme,
        password_hash=password_hash,
        expires_at=share_in.expires_at,
        allowed_domains=share_in.allowed_domains,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    # Add computed fields
    base_url = settings.FRONTEND_URL
    share_response = PublicShareResponse.model_validate(share)
    share_response.public_url = f"{base_url}/public/{share.slug}"
    share_response.has_password = password_hash is not None

    return share_response


@router.get("/shares/{share_id}", response_model=PublicShareResponse)
async def get_public_share(
    db: DBSession,
    current_user: CurrentUser,
    share_id: str,
    request: Request,
) -> PublicShare:
    """Get a specific public share."""
    result = await db.execute(select(PublicShare).where(PublicShare.id == share_id))
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Public share not found")
    if share.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    base_url = settings.FRONTEND_URL
    share_response = PublicShareResponse.model_validate(share)
    share_response.public_url = f"{base_url}/public/{share.slug}"
    share_response.has_password = share.password_hash is not None

    return share_response


@router.patch("/shares/{share_id}", response_model=PublicShareResponse)
async def update_public_share(
    db: DBSession,
    current_user: CurrentUser,
    share_id: str,
    share_in: PublicShareUpdate,
    request: Request,
) -> PublicShare:
    """Update a public share."""
    result = await db.execute(select(PublicShare).where(PublicShare.id == share_id))
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Public share not found")
    if share.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = share_in.model_dump(exclude_unset=True)

    # Handle password update
    if "password" in update_data:
        if update_data["password"]:
            update_data["password_hash"] = get_password_hash(update_data["password"])
        else:
            update_data["password_hash"] = None
        del update_data["password"]

    for field, value in update_data.items():
        setattr(share, field, value)

    await db.commit()
    await db.refresh(share)

    base_url = settings.FRONTEND_URL
    share_response = PublicShareResponse.model_validate(share)
    share_response.public_url = f"{base_url}/public/{share.slug}"
    share_response.has_password = share.password_hash is not None

    return share_response


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_public_share(
    db: DBSession,
    current_user: CurrentUser,
    share_id: str,
) -> None:
    """Delete a public share."""
    result = await db.execute(select(PublicShare).where(PublicShare.id == share_id))
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Public share not found")
    if share.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(share)
    await db.commit()


# ============== EMBED WIDGETS ==============


@router.get("/widgets", response_model=list[EmbedWidgetResponse])
async def list_embed_widgets(
    db: DBSession,
    current_user: CurrentUser,
) -> list[EmbedWidget]:
    """List all embed widgets for the current user."""
    result = await db.execute(
        select(EmbedWidget)
        .where(EmbedWidget.owner_id == current_user.id)
        .order_by(EmbedWidget.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/widgets", response_model=EmbedWidgetResponse, status_code=status.HTTP_201_CREATED)
async def create_embed_widget(
    db: DBSession,
    current_user: CurrentUser,
    widget_in: EmbedWidgetCreate,
    request: Request,
) -> EmbedWidget:
    """Create a new embed widget."""
    # Verify index ownership
    result = await db.execute(select(Index).where(Index.id == widget_in.index_id))
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    if index.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    widget_count = await db.scalar(
        select(func.count(EmbedWidget.id)).where(EmbedWidget.owner_id == current_user.id)
    )
    require_capacity(current_user.tier, "max_embed_widgets", widget_count or 0, "embed widget")
    if widget_in.hide_branding:
        require_feature(current_user.tier, FEATURE_WHITE_LABEL)

    widget = EmbedWidget(
        index_id=widget_in.index_id,
        owner_id=current_user.id,
        name=widget_in.name,
        widget_type=widget_in.widget_type,
        embed_token=generate_embed_token(),
        width=widget_in.width,
        height=widget_in.height,
        theme=widget_in.theme,
        primary_color=widget_in.primary_color,
        background_color=widget_in.background_color,
        font_family=widget_in.font_family,
        hide_branding=widget_in.hide_branding,
        chart_type=widget_in.chart_type,
        show_volume=widget_in.show_volume,
        show_legend=widget_in.show_legend,
        default_period=widget_in.default_period,
        allowed_domains=widget_in.allowed_domains,
    )
    db.add(widget)
    await db.commit()
    await db.refresh(widget)

    base_url = settings.FRONTEND_URL
    widget_response = EmbedWidgetResponse.model_validate(widget)
    widget_response.embed_code = widget.get_embed_code(base_url)

    return widget_response


@router.get("/widgets/{widget_id}", response_model=EmbedWidgetResponse)
async def get_embed_widget(
    db: DBSession,
    current_user: CurrentUser,
    widget_id: str,
    request: Request,
) -> EmbedWidget:
    """Get a specific embed widget."""
    result = await db.execute(select(EmbedWidget).where(EmbedWidget.id == widget_id))
    widget = result.scalar_one_or_none()

    if not widget:
        raise HTTPException(status_code=404, detail="Embed widget not found")
    if widget.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    base_url = settings.FRONTEND_URL
    widget_response = EmbedWidgetResponse.model_validate(widget)
    widget_response.embed_code = widget.get_embed_code(base_url)

    return widget_response


@router.patch("/widgets/{widget_id}", response_model=EmbedWidgetResponse)
async def update_embed_widget(
    db: DBSession,
    current_user: CurrentUser,
    widget_id: str,
    widget_in: EmbedWidgetUpdate,
    request: Request,
) -> EmbedWidget:
    """Update an embed widget."""
    result = await db.execute(select(EmbedWidget).where(EmbedWidget.id == widget_id))
    widget = result.scalar_one_or_none()

    if not widget:
        raise HTTPException(status_code=404, detail="Embed widget not found")
    if widget.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = widget_in.model_dump(exclude_unset=True)
    if update_data.get("hide_branding"):
        require_feature(current_user.tier, FEATURE_WHITE_LABEL)
    for field, value in update_data.items():
        setattr(widget, field, value)

    await db.commit()
    await db.refresh(widget)

    base_url = settings.FRONTEND_URL
    widget_response = EmbedWidgetResponse.model_validate(widget)
    widget_response.embed_code = widget.get_embed_code(base_url)

    return widget_response


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_embed_widget(
    db: DBSession,
    current_user: CurrentUser,
    widget_id: str,
) -> None:
    """Delete an embed widget."""
    result = await db.execute(select(EmbedWidget).where(EmbedWidget.id == widget_id))
    widget = result.scalar_one_or_none()

    if not widget:
        raise HTTPException(status_code=404, detail="Embed widget not found")
    if widget.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(widget)
    await db.commit()


@router.post("/widgets/{widget_id}/regenerate-token", response_model=EmbedWidgetResponse)
async def regenerate_embed_token(
    db: DBSession,
    current_user: CurrentUser,
    widget_id: str,
    request: Request,
) -> EmbedWidget:
    """Regenerate the embed token for a widget."""
    result = await db.execute(select(EmbedWidget).where(EmbedWidget.id == widget_id))
    widget = result.scalar_one_or_none()

    if not widget:
        raise HTTPException(status_code=404, detail="Embed widget not found")
    if widget.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    widget.embed_token = generate_embed_token()
    await db.commit()
    await db.refresh(widget)

    base_url = settings.FRONTEND_URL
    widget_response = EmbedWidgetResponse.model_validate(widget)
    widget_response.embed_code = widget.get_embed_code(base_url)

    return widget_response


# ============================================================================
# Public views (no authentication)
# ============================================================================
#
# These back the pages a share link or an embed iframe actually loads. Without
# them every link the endpoints above hand out led nowhere.


async def _public_index_payload(
    index: Index,
    *,
    show_chart: bool,
    show_components: bool,
    show_performance: bool,
    period: str = "1Y",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": index.name,
        "identifier": index.identifier,
        "description": index.description,
        "currency": index.currency,
        "current_value": index.current_value,
        "base_value": index.base_value,
        "weighting_method": index.weighting_method,
        "rebalance_frequency": index.rebalance_frequency,
        "last_calculated": index.last_calculated,
        "component_count": sum(1 for c in index.components if c.is_active),
        "components": None,
        "series": None,
        "stats": None,
        "as_of": None,
    }

    if show_components:
        payload["components"] = [
            {"ticker": c.ticker, "name": c.name, "sector": c.sector, "weight": c.weight}
            for c in index.components
            if c.is_active
        ]

    if show_chart or show_performance:
        try:
            analytics = await analytics_service.compute_index_analytics(index, period)
        except AnalyticsUnavailableError:
            analytics = None
        if analytics:
            payload["as_of"] = analytics["as_of"]
            if show_chart:
                payload["series"] = [
                    {"date": p["date"], "value": p["value"]} for p in analytics["series"]
                ]
            if show_performance:
                keys = (
                    "total_return",
                    "annualized_return",
                    "volatility",
                    "max_drawdown",
                    "sharpe_ratio",
                )
                payload["stats"] = {k: analytics["stats"][k] for k in keys}

    return payload


@router.get("/public/shares/{slug}")
async def view_public_share(
    db: DBSession,
    slug: str,
    password: str | None = None,
) -> dict[str, Any]:
    """Public read-only view of a shared index."""
    result = await db.execute(
        select(PublicShare)
        .where(PublicShare.slug == slug)
        .options(
            selectinload(PublicShare.index).selectinload(Index.components),
            selectinload(PublicShare.owner),
        )
        # The follower count is computed in SQL; always take the fresh value.
        .execution_options(populate_existing=True)
    )
    share = result.scalar_one_or_none()

    # One response for "never existed", "switched off" and "expired": the link's
    # holder learns only that it does not work.
    expired = bool(share and share.expires_at and share.expires_at < datetime.now(timezone.utc))
    if not share or not share.is_active or expired:
        raise HTTPException(status_code=404, detail="This share link is not available.")

    if share.password_hash:
        if not password:
            raise HTTPException(
                status_code=401,
                detail={"code": "password_required", "message": "This page is protected."},
            )
        if not verify_password(password, share.password_hash):
            raise HTTPException(
                status_code=401,
                detail={"code": "password_invalid", "message": "Incorrect password."},
            )

    # Read before the write below: updating the row expires this computed
    # column, and reloading it afterwards is not possible from async code.
    follower_count = share.follower_count

    share.view_count = (share.view_count or 0) + 1
    share.last_viewed_at = datetime.now(timezone.utc)
    await db.commit()

    payload = await _public_index_payload(
        share.index,
        show_chart=share.show_chart,
        show_components=share.show_components,
        show_performance=share.show_performance,
    )
    payload.update(
        title=share.title_override or share.index.name,
        description=share.description_override or share.index.description,
        theme=share.theme,
        show_branding=not get_plan(share.owner.tier).has(FEATURE_WHITE_LABEL),
        follower_count=follower_count,
    )
    return payload


class FollowRequest(BaseModel):
    email: EmailStr


def _share_summary(share: PublicShare, index: Index) -> dict[str, Any]:
    return {"title": follower_service.share_title(share, index), "slug": share.slug}


@router.post("/public/shares/{slug}/follow", status_code=status.HTTP_202_ACCEPTED)
async def follow_public_share(db: DBSession, slug: str, body: FollowRequest) -> dict[str, str]:
    """
    Ask to be emailed when a shared index is rebalanced.

    Always answers the same way for a valid share, whether or not the address
    was already following, and nothing is sent to the address beyond a
    confirmation link until it is confirmed.
    """
    result = await db.execute(
        select(PublicShare).where(PublicShare.slug == slug).options(selectinload(PublicShare.index))
    )
    share = result.scalar_one_or_none()
    expired = bool(share and share.expires_at and share.expires_at < datetime.now(timezone.utc))
    if not share or not share.is_active or expired:
        raise HTTPException(status_code=404, detail="This share link is not available.")
    # A protected page is shared with a chosen audience; following it would let
    # anyone with the link receive its contents by email without the password.
    if share.password_hash:
        raise HTTPException(status_code=403, detail="This page cannot be followed.")

    await follower_service.request_follow(db, share, share.index, body.email)
    return {"status": "confirmation_sent"}


@router.post("/public/follow/confirm/{token}")
async def confirm_follow(db: DBSession, token: str) -> dict[str, Any]:
    """Confirm a follow request from the emailed link."""
    found = await follower_service.confirm(db, token)
    if not found:
        raise HTTPException(status_code=404, detail="This link is not valid.")
    return _share_summary(*found)


@router.post("/public/follow/unsubscribe/{token}")
async def unsubscribe_follow(db: DBSession, token: str) -> dict[str, Any]:
    """Stop following, from the link in any notification email."""
    found = await follower_service.unsubscribe(db, token)
    if not found:
        # Already removed, or never existed: either way they are not subscribed.
        raise HTTPException(status_code=404, detail="You are not subscribed.")
    return _share_summary(*found)


@router.get("/public/widgets/{embed_token}")
async def view_embed_widget(db: DBSession, embed_token: str) -> dict[str, Any]:
    """Data for an embedded widget, addressed by its embed token."""
    result = await db.execute(
        select(EmbedWidget)
        .where(EmbedWidget.embed_token == embed_token)
        .options(
            selectinload(EmbedWidget.index).selectinload(Index.components),
            selectinload(EmbedWidget.owner),
        )
    )
    widget = result.scalar_one_or_none()
    if not widget or not widget.is_active:
        raise HTTPException(status_code=404, detail="This widget is not available.")

    widget.embed_count = (widget.embed_count or 0) + 1
    widget.last_embedded_at = datetime.now(timezone.utc)
    await db.commit()

    kind = widget.widget_type
    period = widget.default_period if widget.default_period in PERIOD_YEARS else "1Y"
    payload = await _public_index_payload(
        widget.index,
        show_chart=kind in ("chart", "factsheet", "performance"),
        show_components=kind in ("table", "components", "factsheet"),
        show_performance=kind in ("performance", "factsheet"),
        # A free owner's widget is capped at the history their plan includes.
        period=period
        if PERIOD_YEARS[period] <= get_plan(widget.owner.tier).analytics_history_years
        else "1Y",
    )
    payload.update(
        title=widget.index.name,
        widget_type=kind,
        theme=widget.theme,
        primary_color=widget.primary_color,
        background_color=widget.background_color,
        # Removing the badge is a paid feature; a lapsed subscription restores it.
        show_branding=not (
            widget.hide_branding and get_plan(widget.owner.tier).has(FEATURE_WHITE_LABEL)
        ),
    )
    return payload
