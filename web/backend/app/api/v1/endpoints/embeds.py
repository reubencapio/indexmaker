"""
Embeddable Widgets and Public Shares API endpoints.
"""

import secrets

from fastapi import APIRouter, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
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

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        password_hash = pwd_context.hash(share_in.password)

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
    base_url = str(request.base_url).rstrip("/")
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

    base_url = str(request.base_url).rstrip("/")
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
            update_data["password_hash"] = pwd_context.hash(update_data["password"])
        else:
            update_data["password_hash"] = None
        del update_data["password"]

    for field, value in update_data.items():
        setattr(share, field, value)

    await db.commit()
    await db.refresh(share)

    base_url = str(request.base_url).rstrip("/")
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

    base_url = str(request.base_url).rstrip("/")
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

    base_url = str(request.base_url).rstrip("/")
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
    for field, value in update_data.items():
        setattr(widget, field, value)

    await db.commit()
    await db.refresh(widget)

    base_url = str(request.base_url).rstrip("/")
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

    base_url = str(request.base_url).rstrip("/")
    widget_response = EmbedWidgetResponse.model_validate(widget)
    widget_response.embed_code = widget.get_embed_code(base_url)

    return widget_response
