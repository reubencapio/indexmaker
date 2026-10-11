"""
Index management endpoints.

CRUD operations for custom indices and their components.
"""

from datetime import date, datetime, timezone
from typing import Any

import yaml
from fastapi import APIRouter, Body, File, HTTPException, Query, Response, UploadFile, status
from indexforge import SpecError
from indexforge.spec import validate_spec
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload, undefer

from app.api.deps import CurrentUser, DBSession, OptionalUser
from app.core.plans import require_capacity
from app.models.index import Index, IndexComponent, IndexStatus
from app.schemas.index import (
    IndexComponentCreate,
    IndexComponentResponse,
    IndexCreate,
    IndexListResponse,
    IndexResponse,
    IndexUpdate,
)
from app.services import delivery_service
from app.services.index_service import IndexService

router = APIRouter()


@router.post("", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def create_index(
    db: DBSession,
    current_user: CurrentUser,
    index_in: IndexCreate,
) -> Index:
    """
    Create a new index.

    Creates an index with the specified methodology and optionally
    adds initial components.

    Args:
        index_in: Index configuration

    Returns:
        Created index

    Raises:
        HTTPException: If identifier already exists or limit exceeded
    """
    # Check index limit
    result = await db.execute(select(func.count(Index.id)).where(Index.owner_id == current_user.id))
    count = result.scalar() or 0

    require_capacity(current_user.tier, "max_indices", count, "indices")

    # Check identifier uniqueness
    result = await db.execute(select(Index).where(Index.identifier == index_in.identifier))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index identifier already exists",
        )

    # Create index
    index = Index(
        owner_id=current_user.id,
        name=index_in.name,
        identifier=index_in.identifier,
        description=index_in.description,
        currency=index_in.currency,
        weighting_method=index_in.weighting_method,
        rebalance_frequency=index_in.rebalance_frequency,
        base_date=index_in.base_date,
        base_value=index_in.base_value,
        min_market_cap=index_in.min_market_cap,
        min_avg_volume=index_in.min_avg_volume,
        max_components=index_in.max_components,
        countries=index_in.countries,
        sectors=index_in.sectors,
        max_weight=index_in.max_weight,
        max_sector_weight=index_in.max_sector_weight,
        max_country_weight=index_in.max_country_weight,
        custom_rules=index_in.custom_rules,
    )

    db.add(index)
    await db.flush()  # Get the index ID

    # Add initial components if provided
    if index_in.components:
        for comp_data in index_in.components:
            component = IndexComponent(
                index_id=index.id,
                ticker=comp_data.ticker,
                weight=comp_data.weight,
                target_weight=comp_data.target_weight,
            )
            db.add(component)
    else:
        # Auto-populate components based on universe criteria
        service = IndexService(db)
        components = await service.populate_components(
            index, max_components=index_in.max_components or 50
        )

        # Calculate weights if components were added
        if components:
            await db.flush()
            # Re-fetch index with components for calculation
            result = await db.execute(
                select(Index).where(Index.id == index.id).options(selectinload(Index.components))
            )
            index = result.scalar_one()
            await service.calculate_index(index)

    await db.commit()
    await db.refresh(index)

    # Load components
    result = await db.execute(
        select(Index).where(Index.id == index.id).options(selectinload(Index.components))
    )
    index = result.scalar_one()

    return index


@router.get("", response_model=list[IndexListResponse])
async def list_indices(
    db: DBSession,
    current_user: OptionalUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    public_only: bool = Query(default=False),
) -> list[Index]:
    """
    List indices.

    Returns user's indices or public indices if not authenticated.

    Args:
        skip: Pagination offset
        limit: Maximum results
        status_filter: Filter by status (draft, active, etc.)
        public_only: Only return public indices
    """
    # Subquery for component count
    count_stmt = (
        select(func.count(IndexComponent.id))
        .where(IndexComponent.index_id == Index.id)
        .where(IndexComponent.is_active == True)  # noqa: E712
        .label("component_count")
    )

    # Select Index and the count
    query = select(Index, count_stmt)

    if current_user and not public_only:
        # User can see their own indices
        query = query.where(Index.owner_id == current_user.id)
    else:
        # Only public indices
        query = query.where(Index.is_public == True)  # noqa: E712

    if status_filter:
        query = query.where(Index.status == status_filter)

    query = query.order_by(Index.updated_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    # Construct response with count
    indices = []
    for index, count in rows:
        index.component_count = count
        indices.append(index)

    return indices


@router.get("/{index_id}", response_model=IndexResponse)
async def get_index(
    db: DBSession,
    current_user: OptionalUser,
    index_id: str,
) -> Index:
    """
    Get index by ID.

    Returns full index details including components.
    """
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    # Check access
    if not index.is_public and (not current_user or index.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    index.component_count = len([c for c in index.components if c.is_active])
    return index


@router.patch("/{index_id}", response_model=IndexResponse)
async def update_index(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    index_update: IndexUpdate,
) -> Index:
    """
    Update an index.

    Only the owner can update an index.
    """
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    if index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    update_data = index_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(index, field, value)

    await db.commit()
    await db.refresh(index)

    index.component_count = len([c for c in index.components if c.is_active])
    return index


@router.delete("/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
) -> None:
    """Delete an index and all its components."""
    result = await db.execute(select(Index).where(Index.id == index_id))
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    if index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await db.delete(index)
    await db.commit()


# Component endpoints
@router.post("/{index_id}/components", response_model=IndexComponentResponse)
async def add_component(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    component_in: IndexComponentCreate,
) -> IndexComponent:
    """Add a component to an index."""
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    if index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Check max components
    active_count = len([c for c in index.components if c.is_active])
    if active_count >= index.max_components:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum components ({index.max_components}) reached",
        )

    # Check if ticker already exists
    existing = next(
        (c for c in index.components if c.ticker == component_in.ticker and c.is_active),
        None,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Component {component_in.ticker} already exists",
        )

    # Fetch market data for the component
    service = IndexService(db)
    market_data = await service.fetch_component_data(component_in.ticker)

    component = IndexComponent(
        index_id=index.id,
        ticker=component_in.ticker,
        name=market_data.get("name"),
        sector=market_data.get("sector"),
        industry=market_data.get("industry"),
        country=market_data.get("country"),
        market_cap=market_data.get("market_cap"),
        price=market_data.get("price"),
        avg_volume=market_data.get("avg_volume"),
        weight=component_in.weight,
        target_weight=component_in.target_weight,
    )

    db.add(component)
    await db.commit()
    await db.refresh(component)

    return component


@router.delete("/{index_id}/components/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_component(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    ticker: str,
) -> None:
    """Remove a component from an index."""
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    if index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    component = next(
        (c for c in index.components if c.ticker == ticker and c.is_active),
        None,
    )

    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    await db.delete(component)
    await db.commit()


@router.post("/{index_id}/calculate", response_model=IndexResponse)
async def calculate_index(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
) -> Index:
    """
    Calculate/recalculate index values.

    Fetches latest market data and recalculates weights and values.
    """
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    if index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    service = IndexService(db)
    await service.calculate_index(index)

    await db.commit()
    # Reload with constituents: refresh() alone leaves them unloaded, and both the
    # webhook payload and the response read them.
    result = await db.execute(
        select(Index)
        .where(Index.id == index_id)
        .options(selectinload(Index.components))
        .execution_options(populate_existing=True)
    )
    index = result.scalar_one()
    await delivery_service.dispatch_index_event(db, index, delivery_service.EVENT_INDEX_UPDATE)

    index.component_count = len([c for c in index.components if c.is_active])
    return index


# Guideline document endpoints


@router.post("/{index_id}/guideline", response_model=IndexResponse)
async def upload_guideline(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    file: UploadFile = File(...),
) -> Index:
    """
    Upload a guideline document (PDF) for an index.
    """
    import os
    import uuid
    from pathlib import Path

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Limit file size (10MB)
    max_file_size = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit",
        )

    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    if index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Create uploads directory
    uploads_dir = Path("uploads/guidelines")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Delete old file if exists
    if index.guideline_file_path:
        old_path = Path(index.guideline_file_path)
        if old_path.exists():
            old_path.unlink()

    # Save new file
    file_ext = os.path.splitext(file.filename or "document.pdf")[1]
    unique_name = f"{index_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = uploads_dir / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    # Update index
    index.guideline_file_path = str(file_path)
    index.guideline_file_name = file.filename
    index.guideline_file_url = f"/api/v1/indices/{index_id}/guideline/download"

    await db.commit()
    await db.refresh(index)

    index.component_count = len([c for c in index.components if c.is_active])
    return index


@router.get("/{index_id}/guideline/download")
async def download_guideline(
    db: DBSession,
    current_user: OptionalUser,
    index_id: str,
):
    """
    Download the guideline document for an index.
    """
    from pathlib import Path

    from fastapi.responses import FileResponse

    result = await db.execute(select(Index).where(Index.id == index_id))
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    # Check access (owner or public index)
    if not index.is_public:
        if not current_user or index.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    if not index.guideline_file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No guideline document uploaded",
        )

    file_path = Path(index.guideline_file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return FileResponse(
        path=file_path,
        filename=index.guideline_file_name or "guideline.pdf",
        media_type="application/pdf",
    )


@router.delete("/{index_id}/guideline", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guideline(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
):
    """
    Delete the guideline document for an index.
    """
    from pathlib import Path

    result = await db.execute(select(Index).where(Index.id == index_id))
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found",
        )

    if index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if index.guideline_file_path:
        file_path = Path(index.guideline_file_path)
        if file_path.exists():
            file_path.unlink()

    index.guideline_file_path = None
    index.guideline_file_name = None
    index.guideline_file_url = None

    await db.commit()


# ==================== Specs: build, export, reproduce ====================


async def _owned_index(db: DBSession, index_id: str, user_id: str, *options: Any) -> Index:
    """Load an index the caller owns, or raise 404/403."""
    result = await db.execute(select(Index).where(Index.id == index_id).options(*options))
    index = result.scalar_one_or_none()
    if not index:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
    if index.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return index


def _download(body: str, media_type: str, filename: str) -> Response:
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/from-spec", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def create_index_from_spec(
    db: DBSession,
    current_user: CurrentUser,
    payload: dict[str, Any] = Body(..., description="An indexforge spec"),
) -> Index:
    """
    Create an index from an indexforge spec.

    The spec is the whole definition: the same spec, with the same market data,
    always produces the same index. No AI is involved. The build runs in the
    background; poll the index until its status leaves "building".
    """
    # Imported here: app.tasks imports endpoint modules.
    from app.tasks import build_index_from_spec_task

    count = await db.scalar(select(func.count(Index.id)).where(Index.owner_id == current_user.id))
    require_capacity(current_user.tier, "max_indices", count or 0, "indices")

    try:
        spec = validate_spec(payload)
    except SpecError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    existing = await db.execute(select(Index).where(Index.identifier == spec["identifier"]))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index identifier already exists",
        )

    index = Index(
        owner_id=current_user.id,
        name=spec["name"],
        identifier=spec["identifier"],
        description=spec.get("description"),
        currency=spec["currency"],
        weighting_method=spec["weighting"]["method"],
        rebalance_frequency=spec["rebalancing"]["frequency"],
        base_date=datetime.combine(
            date.fromisoformat(spec["base_date"]), datetime.min.time(), tzinfo=timezone.utc
        ),
        base_value=spec["base_value"],
        status=IndexStatus.BUILDING.value,
        spec=spec,
    )
    db.add(index)
    await db.commit()

    build_index_from_spec_task.delay(index_id=str(index.id), user_id=str(current_user.id))

    result = await db.execute(
        select(Index).where(Index.id == index.id).options(selectinload(Index.components))
    )
    return result.scalar_one()


@router.post("/{index_id}/rebuild", response_model=IndexResponse)
async def rebuild_index(db: DBSession, current_user: CurrentUser, index_id: str) -> Index:
    """
    Rebuild an index from its spec with today's market data.

    The rules do not change; the members may, because the data has.
    """
    from app.tasks import build_index_from_spec_task

    index = await _owned_index(db, index_id, current_user.id, selectinload(Index.components))
    if not index.spec:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This index was created before specs existed and has none to rebuild from.",
        )

    index.status = IndexStatus.BUILDING.value
    index.error_message = None
    await db.commit()

    build_index_from_spec_task.delay(index_id=str(index.id), user_id=str(current_user.id))

    result = await db.execute(
        select(Index).where(Index.id == index.id).options(selectinload(Index.components))
    )
    index = result.scalar_one()
    index.component_count = len([c for c in index.components if c.is_active])
    return index


@router.get("/{index_id}/spec")
async def download_spec(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    format: str = Query(default="yaml", pattern="^(yaml|json)$"),
) -> Response:
    """Download the index's spec, ready for `indexforge build`."""
    import json

    index = await _owned_index(db, index_id, current_user.id)
    if not index.spec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This index has no spec")

    name = index.identifier.lower()
    if format == "json":
        return _download(
            json.dumps(index.spec, indent=2) + "\n", "application/json", f"{name}.json"
        )
    body = yaml.safe_dump(index.spec, sort_keys=False, allow_unicode=True)
    return _download(body, "application/yaml", f"{name}.yaml")


@router.get("/{index_id}/build-data")
async def download_build_data(db: DBSession, current_user: CurrentUser, index_id: str) -> Response:
    """
    Download the market data the last build used.

    With the spec, this reproduces the index exactly:
    `indexforge build <spec> --data <this file>`.
    """
    import json

    index = await _owned_index(db, index_id, current_user.id, undefer(Index.build_snapshot))
    if not index.build_snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This index has no recorded build data"
        )

    body = json.dumps(index.build_snapshot, indent=2, sort_keys=True) + "\n"
    return _download(body, "application/json", f"{index.identifier.lower()}.data.json")
