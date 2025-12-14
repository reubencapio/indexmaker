"""
Schemas for corporate actions.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class CorporateActionCreate(BaseModel):
    """Create a corporate action."""

    ticker: str = Field(..., max_length=20)
    action_type: str = Field(..., max_length=50)
    effective_date: date
    announcement_date: date | None = None
    record_date: date | None = None
    ratio: float | None = None
    dividend_amount: float | None = None
    dividend_currency: str | None = Field(default=None, max_length=3)
    target_ticker: str | None = Field(default=None, max_length=20)
    acquirer_ticker: str | None = Field(default=None, max_length=20)
    cash_component: float | None = None
    stock_component: float | None = None
    new_ticker: str | None = Field(default=None, max_length=20)
    new_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    source: str | None = Field(default=None, max_length=100)
    extra_data: dict[str, Any] | None = None


class CorporateActionResponse(BaseModel):
    """Response for corporate action."""

    id: str
    ticker: str
    action_type: str
    effective_date: date
    announcement_date: date | None
    record_date: date | None
    ratio: float | None
    dividend_amount: float | None
    dividend_currency: str | None
    target_ticker: str | None
    acquirer_ticker: str | None
    cash_component: float | None
    stock_component: float | None
    new_ticker: str | None
    new_name: str | None
    status: str
    description: str | None
    source: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ApplyCorporateActionRequest(BaseModel):
    """Request to apply a corporate action to an index."""

    corporate_action_id: str
    apply_to_history: bool = False  # Whether to adjust historical values
