"""
Corporate Actions API endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models.corporate_action import (
    CorporateAction,
    CorporateActionStatus,
    IndexCorporateActionLog,
)
from app.models.index import Index
from app.schemas.corporate_action import (
    CorporateActionCreate,
    CorporateActionResponse,
)

router = APIRouter()


@router.get("/", response_model=list[CorporateActionResponse])
async def list_corporate_actions(
    db: DBSession,
    current_user: CurrentUser,
    ticker: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[CorporateAction]:
    """List corporate actions with optional filters."""
    query = select(CorporateAction).order_by(CorporateAction.effective_date.desc())

    if ticker:
        query = query.where(CorporateAction.ticker == ticker.upper())
    if action_type:
        query = query.where(CorporateAction.action_type == action_type)
    if status:
        query = query.where(CorporateAction.status == status)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=CorporateActionResponse, status_code=status.HTTP_201_CREATED)
async def create_corporate_action(
    db: DBSession,
    current_user: CurrentUser,
    action_in: CorporateActionCreate,
) -> CorporateAction:
    """Create a new corporate action."""
    action = CorporateAction(
        ticker=action_in.ticker.upper(),
        action_type=action_in.action_type,
        effective_date=action_in.effective_date,
        announcement_date=action_in.announcement_date,
        record_date=action_in.record_date,
        ratio=action_in.ratio,
        dividend_amount=action_in.dividend_amount,
        dividend_currency=action_in.dividend_currency,
        target_ticker=action_in.target_ticker,
        acquirer_ticker=action_in.acquirer_ticker,
        cash_component=action_in.cash_component,
        stock_component=action_in.stock_component,
        new_ticker=action_in.new_ticker,
        new_name=action_in.new_name,
        description=action_in.description,
        source=action_in.source,
        extra_data=action_in.extra_data,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


@router.get("/{action_id}", response_model=CorporateActionResponse)
async def get_corporate_action(
    db: DBSession,
    current_user: CurrentUser,
    action_id: str,
) -> CorporateAction:
    """Get a specific corporate action."""
    result = await db.execute(select(CorporateAction).where(CorporateAction.id == action_id))
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")

    return action


@router.post("/{action_id}/apply/{index_id}")
async def apply_corporate_action(
    db: DBSession,
    current_user: CurrentUser,
    action_id: str,
    index_id: str,
    apply_to_history: bool = Query(default=False),
) -> dict:
    """
    Apply a corporate action to an index.

    Handles:
    - Stock splits: Adjust shares and prices
    - Dividends: Track for total return calculation
    - Mergers: Replace target with acquirer
    - Delistings: Remove component
    - Ticker changes: Update ticker symbol
    """
    # Get corporate action
    result = await db.execute(select(CorporateAction).where(CorporateAction.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")

    # Get index with components
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")

    if index.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Find affected component
    affected_component = None
    for comp in index.components:
        if comp.ticker == action.ticker and comp.is_active:
            affected_component = comp
            break

    if not affected_component:
        return {"message": f"Ticker {action.ticker} not found in index", "applied": False}

    action_taken = ""
    old_shares = affected_component.shares
    new_shares = old_shares
    adjustment_factor = 1.0

    # Apply based on action type
    if action.action_type in ["stock_split", "reverse_split"]:
        if action.ratio:
            new_shares = old_shares * action.ratio
            affected_component.shares = new_shares
            if affected_component.price:
                affected_component.price = affected_component.price / action.ratio
            adjustment_factor = action.ratio
            action_taken = (
                f"Applied {action.ratio}:1 split. Shares: {old_shares:.2f} -> {new_shares:.2f}"
            )

    elif action.action_type == "cash_dividend":
        # Record dividend for total return calculation
        action_taken = (
            f"Recorded cash dividend: {action.dividend_currency or 'USD'} {action.dividend_amount}"
        )

    elif action.action_type == "stock_dividend":
        if action.ratio:
            new_shares = old_shares * (1 + action.ratio)
            affected_component.shares = new_shares
            adjustment_factor = 1 + action.ratio
            action_taken = f"Applied {action.ratio*100:.1f}% stock dividend. Shares: {old_shares:.2f} -> {new_shares:.2f}"

    elif action.action_type in ["merger", "acquisition"]:
        if action.acquirer_ticker:
            # Check if acquirer already in index
            acquirer_exists = any(
                c.ticker == action.acquirer_ticker and c.is_active for c in index.components
            )

            if acquirer_exists:
                # Merge into existing position
                affected_component.is_active = False
                affected_component.removed_date = datetime.now(timezone.utc)
                action_taken = (
                    f"Merged {action.ticker} into existing {action.acquirer_ticker} position"
                )
            else:
                # Replace ticker
                affected_component.ticker = action.acquirer_ticker
                if action.stock_component:
                    affected_component.shares = old_shares * action.stock_component
                action_taken = f"Replaced {action.ticker} with {action.acquirer_ticker}"

    elif action.action_type == "delisting":
        affected_component.is_active = False
        affected_component.removed_date = datetime.now(timezone.utc)
        action_taken = f"Removed {action.ticker} due to delisting"

    elif action.action_type == "ticker_change":
        if action.new_ticker:
            old_ticker = affected_component.ticker
            affected_component.ticker = action.new_ticker
            if action.new_name:
                affected_component.name = action.new_name
            action_taken = f"Changed ticker from {old_ticker} to {action.new_ticker}"

    elif action.action_type == "name_change":
        if action.new_name:
            affected_component.name = action.new_name
            action_taken = f"Changed name to {action.new_name}"

    # Log the action
    log = IndexCorporateActionLog(
        index_id=index_id,
        corporate_action_id=action_id,
        action_taken=action_taken,
        old_shares=old_shares,
        new_shares=new_shares,
        adjustment_factor=adjustment_factor,
    )
    db.add(log)

    # Mark action as applied
    action.status = CorporateActionStatus.APPLIED.value

    await db.commit()

    return {
        "message": action_taken,
        "applied": True,
        "adjustment_factor": adjustment_factor,
    }


@router.get("/pending/for-index/{index_id}")
async def get_pending_actions_for_index(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
) -> list[CorporateActionResponse]:
    """Get pending corporate actions that affect an index's components."""
    # Get index components
    result = await db.execute(
        select(Index).where(Index.id == index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")

    if index.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get active tickers
    tickers = [c.ticker for c in index.components if c.is_active]

    if not tickers:
        return []

    # Find pending actions for these tickers
    result = await db.execute(
        select(CorporateAction)
        .where(CorporateAction.ticker.in_(tickers))
        .where(CorporateAction.status == CorporateActionStatus.PENDING.value)
        .order_by(CorporateAction.effective_date)
    )

    return list(result.scalars().all())
