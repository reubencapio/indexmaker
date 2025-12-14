"""
Custom Data Source schemas for API validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SecurityData(BaseModel):
    """Schema for individual security data."""
    
    ticker: str = Field(..., max_length=50)
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    exchange: str | None = None
    market_cap: float | None = None
    price: float | None = None
    avg_volume: float | None = None
    free_float: float | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    dividend_yield: float | None = None
    revenue: float | None = None
    earnings: float | None = None
    custom_fields: dict[str, Any] | None = None


class DataSourceCreate(BaseModel):
    """Schema for creating a custom data source."""
    
    name: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    source_type: str = Field(default="ticker_list")
    config: dict[str, Any] | None = None
    field_mapping: dict[str, str] | None = None


class DataSourceUpdate(BaseModel):
    """Schema for updating a data source."""
    
    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    config: dict[str, Any] | None = None
    field_mapping: dict[str, str] | None = None
    is_active: bool | None = None


class DataSourceAddSecurities(BaseModel):
    """Schema for adding securities to a data source."""
    
    securities: list[SecurityData]


class DataSourceImportCSV(BaseModel):
    """Schema for CSV import configuration."""
    
    # Field mapping from CSV columns to our fields
    ticker_column: str = Field(default="ticker")
    name_column: str | None = "name"
    sector_column: str | None = None
    industry_column: str | None = None
    country_column: str | None = None
    market_cap_column: str | None = None
    price_column: str | None = None


class CustomSecurityResponse(BaseModel):
    """Schema for security response."""
    
    id: str
    ticker: str
    name: str | None
    sector: str | None
    industry: str | None
    country: str | None
    exchange: str | None
    market_cap: float | None
    price: float | None
    avg_volume: float | None
    free_float: float | None
    is_active: bool
    
    class Config:
        from_attributes = True


class DataSourceResponse(BaseModel):
    """Schema for data source response."""
    
    id: str
    name: str
    description: str | None
    source_type: str
    config: dict[str, Any] | None
    field_mapping: dict[str, str] | None
    securities_count: int
    last_synced: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DataSourceDetailResponse(DataSourceResponse):
    """Schema for detailed data source response with securities."""
    
    securities: list[CustomSecurityResponse] = []

