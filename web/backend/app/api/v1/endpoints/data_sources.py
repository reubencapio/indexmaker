"""
Custom Data Source endpoints.

Allows users to manage their own security databases/universes.
"""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models.data_source import CustomDataSource, CustomSecurity, DataSourceType
from app.schemas.data_source import (
    CustomSecurityResponse,
    DataSourceAddSecurities,
    DataSourceCreate,
    DataSourceDetailResponse,
    DataSourceResponse,
    DataSourceUpdate,
)
from app.services.data_source_service import DataSourceService

router = APIRouter()


@router.post("/", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    db: DBSession,
    current_user: CurrentUser,
    data_source_in: DataSourceCreate,
) -> CustomDataSource:
    """
    Create a new custom data source.

    Allows users to define their own universe of securities.
    """
    # Check limit (free tier: 2, pro: 10, enterprise: unlimited)
    result = await db.execute(
        select(func.count(CustomDataSource.id)).where(CustomDataSource.owner_id == current_user.id)
    )
    count = result.scalar() or 0

    limits = {"free": 2, "pro": 10, "enterprise": 1000}
    max_sources = limits.get(current_user.tier, 2)

    if count >= max_sources:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Data source limit reached ({max_sources}). Upgrade to create more.",
        )

    data_source = CustomDataSource(
        owner_id=current_user.id,
        name=data_source_in.name,
        description=data_source_in.description,
        source_type=data_source_in.source_type,
        config=data_source_in.config,
        field_mapping=data_source_in.field_mapping,
    )

    db.add(data_source)
    await db.commit()
    await db.refresh(data_source)

    return data_source


@router.get("/", response_model=list[DataSourceResponse])
async def list_data_sources(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[CustomDataSource]:
    """List user's custom data sources."""
    query = (
        select(CustomDataSource)
        .where(CustomDataSource.owner_id == current_user.id)
        .order_by(CustomDataSource.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{data_source_id}", response_model=DataSourceDetailResponse)
async def get_data_source(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
) -> CustomDataSource:
    """Get data source details with securities."""
    result = await db.execute(
        select(CustomDataSource)
        .where(CustomDataSource.id == data_source_id)
        .options(selectinload(CustomDataSource.securities))
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return data_source


@router.patch("/{data_source_id}", response_model=DataSourceResponse)
async def update_data_source(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
    update_data: DataSourceUpdate,
) -> CustomDataSource:
    """Update a data source."""
    result = await db.execute(select(CustomDataSource).where(CustomDataSource.id == data_source_id))
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(data_source, field, value)

    await db.commit()
    await db.refresh(data_source)

    return data_source


@router.delete("/{data_source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
) -> None:
    """Delete a data source and all its securities."""
    result = await db.execute(select(CustomDataSource).where(CustomDataSource.id == data_source_id))
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await db.delete(data_source)
    await db.commit()


@router.post("/{data_source_id}/securities", response_model=DataSourceResponse)
async def add_securities(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
    securities_data: DataSourceAddSecurities,
) -> CustomDataSource:
    """
    Add securities to a data source.

    Can be used to manually add securities or from a parsed CSV.
    """
    result = await db.execute(
        select(CustomDataSource)
        .where(CustomDataSource.id == data_source_id)
        .options(selectinload(CustomDataSource.securities))
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get existing tickers to avoid duplicates
    existing_tickers = {s.ticker for s in data_source.securities}

    added_count = 0
    for sec_data in securities_data.securities:
        if sec_data.ticker in existing_tickers:
            continue

        security = CustomSecurity(
            data_source_id=data_source.id,
            ticker=sec_data.ticker,
            name=sec_data.name,
            sector=sec_data.sector,
            industry=sec_data.industry,
            country=sec_data.country,
            exchange=sec_data.exchange,
            market_cap=sec_data.market_cap,
            price=sec_data.price,
            avg_volume=sec_data.avg_volume,
            free_float=sec_data.free_float,
            pe_ratio=sec_data.pe_ratio,
            pb_ratio=sec_data.pb_ratio,
            dividend_yield=sec_data.dividend_yield,
            revenue=sec_data.revenue,
            earnings=sec_data.earnings,
            custom_fields=sec_data.custom_fields,
        )
        db.add(security)
        added_count += 1

    # Update count and sync time
    data_source.securities_count = len(existing_tickers) + added_count
    data_source.last_synced = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(data_source)

    return data_source


@router.post("/{data_source_id}/import-csv", response_model=DataSourceResponse)
async def import_csv(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
    file: UploadFile = File(...),
    ticker_column: str = Query(default="ticker"),
    name_column: str | None = Query(default="name"),
    sector_column: str | None = Query(default=None),
    country_column: str | None = Query(default=None),
    market_cap_column: str | None = Query(default=None),
    price_column: str | None = Query(default=None),
) -> CustomDataSource:
    """
    Import securities from a CSV file.

    Specify which columns map to which fields.
    """
    result = await db.execute(
        select(CustomDataSource)
        .where(CustomDataSource.id == data_source_id)
        .options(selectinload(CustomDataSource.securities))
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Read CSV
    try:
        contents = await file.read()
        decoded = contents.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))

        existing_tickers = {s.ticker for s in data_source.securities}
        added_count = 0

        for row in reader:
            ticker = row.get(ticker_column, "").strip().upper()
            if not ticker or ticker in existing_tickers:
                continue

            security = CustomSecurity(
                data_source_id=data_source.id,
                ticker=ticker,
                name=row.get(name_column) if name_column else None,
                sector=row.get(sector_column) if sector_column else None,
                country=row.get(country_column) if country_column else None,
                market_cap=_parse_float(row.get(market_cap_column)) if market_cap_column else None,
                price=_parse_float(row.get(price_column)) if price_column else None,
            )
            db.add(security)
            existing_tickers.add(ticker)
            added_count += 1

        data_source.securities_count = len(existing_tickers)
        data_source.last_synced = datetime.now(timezone.utc)
        data_source.source_type = DataSourceType.CSV_UPLOAD.value

        await db.commit()
        await db.refresh(data_source)

        return data_source

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(e)}",
        )


@router.delete("/{data_source_id}/securities/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_security(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
    ticker: str,
) -> None:
    """Remove a security from a data source."""
    result = await db.execute(select(CustomDataSource).where(CustomDataSource.id == data_source_id))
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    result = await db.execute(
        select(CustomSecurity).where(
            CustomSecurity.data_source_id == data_source_id,
            CustomSecurity.ticker == ticker.upper(),
        )
    )
    security = result.scalar_one_or_none()

    if not security:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security not found",
        )

    await db.delete(security)

    # Update count
    data_source.securities_count = max(0, data_source.securities_count - 1)

    await db.commit()


@router.get("/{data_source_id}/securities", response_model=list[CustomSecurityResponse])
async def list_securities(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None),
) -> list[CustomSecurity]:
    """List securities in a data source."""
    # Verify ownership
    result = await db.execute(select(CustomDataSource).where(CustomDataSource.id == data_source_id))
    data_source = result.scalar_one_or_none()

    if not data_source or data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    query = (
        select(CustomSecurity)
        .where(CustomSecurity.data_source_id == data_source_id)
        .where(CustomSecurity.is_active.is_(True))
    )

    if search:
        query = query.where(
            CustomSecurity.ticker.ilike(f"%{search}%") | CustomSecurity.name.ilike(f"%{search}%")
        )

    query = query.order_by(CustomSecurity.ticker).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


def _parse_float(value: str | None) -> float | None:
    """Parse a string to float, handling common formats."""
    if not value:
        return None
    try:
        # Remove commas and currency symbols
        cleaned = value.replace(",", "").replace("$", "").replace("€", "").strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


@router.post("/{data_source_id}/sync-api", response_model=dict)
async def sync_from_api(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
) -> dict:
    """
    Sync securities from an external REST API.

    The data source must have API configuration in its config field:
    - endpoint: API URL
    - method: GET or POST
    - headers: Optional headers (e.g., Authorization)
    - params: Query parameters for GET
    - body: Request body for POST
    - response_path: JSONPath to the securities array in response

    And field_mapping to map API fields to our schema.
    """
    result = await db.execute(select(CustomDataSource).where(CustomDataSource.id == data_source_id))
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if data_source.source_type != DataSourceType.API_ENDPOINT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data source is not configured as API endpoint",
        )

    service = DataSourceService(db)
    try:
        result = await service.sync_from_api(data_source)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{data_source_id}/sync-database", response_model=dict)
async def sync_from_database(
    db: DBSession,
    current_user: CurrentUser,
    data_source_id: str,
) -> dict:
    """
    Sync securities from an external database.

    The data source must have database configuration in its config field:
    - db_type: postgresql or mysql
    - host: Database host
    - port: Database port
    - database: Database name
    - username: Database user
    - password: Database password
    - query: SQL query to fetch securities

    And field_mapping to map column names to our schema.
    """
    result = await db.execute(select(CustomDataSource).where(CustomDataSource.id == data_source_id))
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if data_source.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if data_source.source_type != DataSourceType.DATABASE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data source is not configured as database",
        )

    service = DataSourceService(db)
    try:
        result = await service.sync_from_database(data_source)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/test-api-connection", response_model=dict)
async def test_api_connection(
    db: DBSession,
    current_user: CurrentUser,
    config: dict,
) -> dict:
    """
    Test an API connection before saving.

    Config should contain:
    - endpoint: API URL
    - method: GET or POST (optional, defaults to GET)
    - headers: Optional headers
    - params: Optional query params
    """
    service = DataSourceService(db)
    result = await service.test_api_connection(config)
    return result


@router.post("/test-database-connection", response_model=dict)
async def test_database_connection(
    db: DBSession,
    current_user: CurrentUser,
    config: dict,
) -> dict:
    """
    Test a database connection before saving.

    Config should contain:
    - db_type: postgresql or mysql
    - host: Database host
    - port: Database port (optional)
    - database: Database name
    - username: Database user
    - password: Database password
    """
    service = DataSourceService(db)
    result = await service.test_database_connection(config)
    return result
