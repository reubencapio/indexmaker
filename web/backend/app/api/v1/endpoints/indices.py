"""
Index management endpoints.

CRUD operations for custom indices and their components.
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession, OptionalUser
from app.models.index import Index, IndexComponent
from app.schemas.index import (
    IndexComponentCreate,
    IndexComponentResponse,
    IndexCreate,
    IndexListResponse,
    IndexResponse,
    IndexUpdate,
)
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

    if count >= current_user.max_indices:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Index limit reached ({current_user.max_indices}). Upgrade to create more.",
        )

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
    await db.refresh(index)

    index.component_count = len([c for c in index.components if c.is_active])
    return index
