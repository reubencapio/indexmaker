"""
Custom Data Source model for user-defined security universes.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class DataSourceType(str, Enum):
    """Types of custom data sources."""
    
    CSV_UPLOAD = "csv_upload"
    TICKER_LIST = "ticker_list"
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"


class CustomDataSource(Base):
    """
    User-defined data source for securities.
    
    Allows users to bring their own universe of securities
    instead of using the predefined data.
    """
    
    __tablename__ = "custom_data_sources"
    
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(50),
        default=DataSourceType.TICKER_LIST.value,
        nullable=False,
    )
    
    # Configuration based on source type
    # For API: { "endpoint": "...", "api_key": "...", "headers": {...} }
    # For Database: { "host": "...", "port": ..., "database": "...", "query": "..." }
    # For CSV: { "filename": "...", "delimiter": "," }
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    # Field mapping: maps user's field names to our expected fields
    # { "ticker_field": "symbol", "name_field": "company_name", "market_cap_field": "mcap", ... }
    field_mapping: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    
    # Cached securities data from this source
    securities_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="data_sources")
    securities: Mapped[list["CustomSecurity"]] = relationship(
        "CustomSecurity",
        back_populates="data_source",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<CustomDataSource {self.name}>"


class CustomSecurity(Base):
    """
    Individual security from a custom data source.
    """
    
    __tablename__ = "custom_securities"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    data_source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Core fields
    ticker: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Classification
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Market data
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Fundamentals (optional)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    earnings: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Custom fields stored as JSON
    custom_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    data_source: Mapped["CustomDataSource"] = relationship(
        "CustomDataSource",
        back_populates="securities",
    )
    
    def __repr__(self) -> str:
        return f"<CustomSecurity {self.ticker}>"

