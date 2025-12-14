"""
Corporate Actions Model.

Handles stock splits, dividends, mergers, spin-offs, and other corporate events.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CorporateActionType(str, Enum):
    """Types of corporate actions."""
    
    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    CASH_DIVIDEND = "cash_dividend"
    STOCK_DIVIDEND = "stock_dividend"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    SPIN_OFF = "spin_off"
    RIGHTS_ISSUE = "rights_issue"
    DELISTING = "delisting"
    NAME_CHANGE = "name_change"
    TICKER_CHANGE = "ticker_change"


class CorporateActionStatus(str, Enum):
    """Status of corporate action processing."""
    
    PENDING = "pending"
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"


class CorporateAction(Base):
    """
    Represents a corporate action event for a security.
    """
    
    __tablename__ = "corporate_actions"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    
    # The security this action applies to
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Action details
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    announcement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Split/dividend ratio (e.g., 2.0 for 2:1 split, 0.5 for 1:2 reverse split)
    ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # For cash dividends
    dividend_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    
    # For mergers/acquisitions
    target_ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    acquirer_ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cash_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    stock_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # For ticker/name changes
    new_ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), default=CorporateActionStatus.PENDING.value, nullable=False
    )
    
    # Additional metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<CorporateAction {self.action_type} {self.ticker} @ {self.effective_date}>"


class IndexCorporateActionLog(Base):
    """
    Tracks how corporate actions were applied to specific indices.
    """
    
    __tablename__ = "index_corporate_action_logs"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    
    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("indices.id"), nullable=False
    )
    corporate_action_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("corporate_actions.id"), nullable=False
    )
    
    # What was done
    action_taken: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Before/after values for audit
    old_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_shares: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_shares: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjustment_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="corporate_action_logs")
    corporate_action: Mapped["CorporateAction"] = relationship("CorporateAction")
    
    def __repr__(self) -> str:
        return f"<IndexCorporateActionLog {self.index_id} - {self.corporate_action_id}>"

