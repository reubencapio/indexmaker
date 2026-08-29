"""
Index and component models for index management.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.backtest import Backtest
    from app.models.corporate_action import IndexCorporateActionLog
    from app.models.embed import EmbedWidget, PublicShare
    from app.models.organization import Project
    from app.models.report import GeneratedReport
    from app.models.user import User


class IndexStatus(str, Enum):
    """Index lifecycle status."""

    DRAFT = "draft"
    BUILDING = "building"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    ERROR = "error"


class WeightingMethod(str, Enum):
    """Weighting schemes for index calculation."""

    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP = "market_cap"
    FREE_FLOAT_MARKET_CAP = "free_float_market_cap"
    CUSTOM = "custom"


class RebalanceFrequency(str, Enum):
    """Rebalancing frequency options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class Index(Base):
    """
    Index configuration and metadata.

    This is the core entity representing a custom index with its
    methodology, components, and calculation settings.
    """

    __tablename__ = "indices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Project association (optional - for team collaboration)
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    identifier: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Methodology
    weighting_method: Mapped[str] = mapped_column(
        String(50),
        default=WeightingMethod.EQUAL_WEIGHT.value,
    )
    rebalance_frequency: Mapped[str] = mapped_column(
        String(50),
        default=RebalanceFrequency.QUARTERLY.value,
    )
    base_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_value: Mapped[float] = mapped_column(Float, default=1000.0)

    # Universe constraints
    min_market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_avg_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_components: Mapped[int] = mapped_column(Integer, default=100)
    countries: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    sectors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Capping rules
    max_weight: Mapped[float | None] = mapped_column(Float, nullable=True)  # e.g., 0.10 = 10%
    max_sector_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_country_weight: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Custom methodology (JSON for flexibility)
    custom_rules: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Divisor for the index level: level = sum(price * shares) / divisor. Reset on
    # every composition change so the level stays continuous across rebalances and
    # corporate actions. Null until the index is first calculated.
    divisor: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status and metadata
    status: Mapped[str] = mapped_column(
        String(50),
        default=IndexStatus.DRAFT.value,
    )
    # Populated when status is ERROR, so the UI can explain the failure instead of
    # silently showing an empty index.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The description the index was generated from. Kept verbatim so a failed
    # generation can be retried without the user retyping it -- reconstructing it
    # from the mangled placeholder description was never reliable.
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_calculated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Guideline document
    guideline_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    guideline_file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    guideline_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Selection criteria (list of rule strings)
    selection_criteria: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="indices")
    project: Mapped["Project"] = relationship("Project", back_populates="indices")
    components: Mapped[list["IndexComponent"]] = relationship(
        "IndexComponent",
        back_populates="index",
        cascade="all, delete-orphan",
        order_by="IndexComponent.weight.desc()",
    )
    snapshots: Mapped[list["IndexSnapshot"]] = relationship(
        "IndexSnapshot",
        back_populates="index",
        cascade="all, delete-orphan",
        order_by="IndexSnapshot.date.desc()",
    )
    backtests: Mapped[list["Backtest"]] = relationship(
        "Backtest",
        back_populates="index",
        cascade="all, delete-orphan",
    )
    corporate_action_logs: Mapped[list["IndexCorporateActionLog"]] = relationship(
        "IndexCorporateActionLog",
        back_populates="index",
        cascade="all, delete-orphan",
    )
    public_shares: Mapped[list["PublicShare"]] = relationship(
        "PublicShare",
        back_populates="index",
        cascade="all, delete-orphan",
    )
    embed_widgets: Mapped[list["EmbedWidget"]] = relationship(
        "EmbedWidget",
        back_populates="index",
        cascade="all, delete-orphan",
    )
    generated_reports: Mapped[list["GeneratedReport"]] = relationship(
        "GeneratedReport",
        back_populates="index",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Index {self.identifier}: {self.name}>"


class IndexComponent(Base):
    """
    Individual component (security) within an index.

    Tracks the current and target weights, along with security metadata.
    """

    __tablename__ = "index_components"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("indices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Security identifiers
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)

    # Classification
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Market data (cached)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_volume: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Weight
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    target_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares: Mapped[float] = mapped_column(Float, default=0.0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    removed_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="components")

    def __repr__(self) -> str:
        return f"<IndexComponent {self.ticker}: {self.weight:.2%}>"


class IndexSnapshot(Base):
    """
    Historical snapshot of index values and composition.

    Used for tracking index performance over time and backtesting.
    """

    __tablename__ = "index_snapshots"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("indices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshot data
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Component weights at this point in time
    component_weights: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)

    # Metadata
    is_rebalance_day: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<IndexSnapshot {self.date.date()}: {self.value:.2f}>"
