"""
Backtest endpoints.

Run and manage historical backtests for indices.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models.backtest import Backtest, BacktestStatus
from app.models.index import Index
from app.schemas.backtest import BacktestCreate, BacktestListResponse, BacktestResponse
from app.services.backtest_service import BacktestService

router = APIRouter()


@router.post("", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
async def create_backtest(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    backtest_in: BacktestCreate,
    background_tasks: BackgroundTasks,
) -> Backtest:
    """
    Create and run a new backtest.

    The backtest runs asynchronously in the background.
    Poll the status endpoint to check progress.

    Args:
        index_id: ID of the index to backtest
        backtest_in: Backtest configuration

    Returns:
        Created backtest (status will be 'pending' or 'running')
    """
    # Verify index ownership
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

    # Validate date range
    if backtest_in.start_date >= backtest_in.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date",
        )

    # Create backtest record
    backtest = Backtest(
        index_id=index.id,
        name=backtest_in.name,
        start_date=backtest_in.start_date,
        end_date=backtest_in.end_date,
        initial_value=backtest_in.initial_value,
        benchmark_ticker=backtest_in.benchmark_ticker,
        status=BacktestStatus.PENDING.value,
    )

    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)

    # Queue background task
    background_tasks.add_task(run_backtest_task, backtest.id)

    return backtest


async def run_backtest_task(backtest_id: str) -> None:
    """
    Background task to run a backtest.

    This is a simplified version - in production, use Celery.
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as db:
        service = BacktestService(db)
        await service.run_backtest(backtest_id)
        await db.commit()


@router.get("", response_model=list[BacktestListResponse])
async def list_backtests(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[Backtest]:
    """
    List backtests.

    Args:
        index_id: Filter by index ID
        skip: Pagination offset
        limit: Maximum results
    """
    query = (
        select(Backtest)
        .join(Index)
        .where(Index.owner_id == current_user.id)
        .order_by(Backtest.created_at.desc())
    )

    if index_id:
        query = query.where(Backtest.index_id == index_id)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    db: DBSession,
    current_user: CurrentUser,
    backtest_id: str,
) -> Backtest:
    """
    Get backtest details including results.

    Returns full backtest data with time series for charting.
    """
    result = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id).options(selectinload(Backtest.index))
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    if backtest.index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return backtest


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(
    db: DBSession,
    current_user: CurrentUser,
    backtest_id: str,
) -> None:
    """Delete a backtest."""
    result = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id).options(selectinload(Backtest.index))
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    if backtest.index.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await db.delete(backtest)
    await db.commit()


@router.get("/{backtest_id}/status")
async def get_backtest_status(
    db: DBSession,
    current_user: CurrentUser,
    backtest_id: str,
) -> dict:
    """
    Get backtest status for polling.

    Lightweight endpoint for checking progress.
    """
    result = await db.execute(
        select(Backtest.status, Backtest.progress, Backtest.error_message).where(
            Backtest.id == backtest_id
        )
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    return {
        "status": row.status,
        "progress": row.progress,
        "error_message": row.error_message,
    }
