"""
Index schemas for API validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IndexComponentCreate(BaseModel):
    """Schema for adding a component to an index."""

    ticker: str = Field(..., max_length=20)
    weight: float = Field(default=0.0, ge=0, le=1)
    target_weight: float | None = Field(default=None, ge=0, le=1)


class IndexComponentResponse(BaseModel):
    """Schema for component response."""

    id: str
    ticker: str
    name: str | None
    sector: str | None
    industry: str | None
    country: str | None
    market_cap: float | None
    price: float | None
    weight: float
    target_weight: float | None
    is_active: bool
    added_date: datetime

    class Config:
        from_attributes = True


class IndexCreate(BaseModel):
    """Schema for creating a new index."""

    name: str = Field(..., min_length=3, max_length=255)
    identifier: str = Field(..., min_length=2, max_length=50, pattern=r"^[A-Z0-9_]+$")
    description: str | None = None
    currency: str = Field(default="USD", max_length=3)

    # Methodology
    weighting_method: str = Field(default="equal_weight")
    rebalance_frequency: str = Field(default="quarterly")
    base_date: datetime
    base_value: float = Field(default=1000.0, gt=0)

    # Universe constraints
    min_market_cap: float | None = Field(default=None, ge=0)
    min_avg_volume: float | None = Field(default=None, ge=0)
    max_components: int = Field(default=100, ge=1, le=500)
    countries: list[str] | None = None
    sectors: list[str] | None = None

    # Capping
    max_weight: float | None = Field(default=None, ge=0, le=1)
    max_sector_weight: float | None = Field(default=None, ge=0, le=1)
    max_country_weight: float | None = Field(default=None, ge=0, le=1)

    # Components
    components: list[IndexComponentCreate] | None = None

    # Custom rules
    custom_rules: dict[str, Any] | None = None


class IndexUpdate(BaseModel):
    """Schema for updating an index."""

    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None

    # Methodology
    weighting_method: str | None = None
    rebalance_frequency: str | None = None

    # Universe constraints
    min_market_cap: float | None = None
    min_avg_volume: float | None = None
    max_components: int | None = Field(default=None, ge=1, le=500)
    countries: list[str] | None = None
    sectors: list[str] | None = None

    # Capping
    max_weight: float | None = None
    max_sector_weight: float | None = None
    max_country_weight: float | None = None

    # Status
    status: str | None = None
    is_public: bool | None = None

    # Custom rules
    custom_rules: dict[str, Any] | None = None


class IndexSnapshotResponse(BaseModel):
    """Schema for index snapshot response."""

    id: str
    date: datetime
    value: float
    daily_return: float | None
    is_rebalance_day: bool

    class Config:
        from_attributes = True


class IndexResponse(BaseModel):
    """Schema for index response."""

    id: str
    owner_id: str
    name: str
    identifier: str
    description: str | None
    currency: str

    # Methodology
    weighting_method: str
    rebalance_frequency: str
    base_date: datetime
    base_value: float

    # Universe
    min_market_cap: float | None
    min_avg_volume: float | None
    max_components: int
    countries: list[str] | None
    sectors: list[str] | None

    # Capping
    max_weight: float | None
    max_sector_weight: float | None
    max_country_weight: float | None

    # Custom rules (includes theme_keywords for thematic indices)
    custom_rules: dict[str, Any] | None = None

    # Status
    status: str
    is_public: bool
    current_value: float | None
    last_calculated: datetime | None
    created_at: datetime
    updated_at: datetime

    # Nested
    components: list[IndexComponentResponse] = []
    component_count: int = 0

    class Config:
        from_attributes = True


class IndexListResponse(BaseModel):
    """Schema for index list response."""

    id: str
    name: str
    identifier: str
    currency: str
    weighting_method: str
    status: str
    is_public: bool
    current_value: float | None
    component_count: int
    created_at: datetime

    class Config:
        from_attributes = True
