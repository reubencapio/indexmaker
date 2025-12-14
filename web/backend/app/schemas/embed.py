"""
Schemas for embeddable widgets and public shares.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# Public Share Schemas
class PublicShareCreate(BaseModel):
    """Create a public share link."""

    index_id: str
    slug: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[a-z0-9-]+$")
    show_chart: bool = True
    show_components: bool = True
    show_performance: bool = True
    show_factsheet: bool = False
    allow_download: bool = False
    title_override: str | None = Field(default=None, max_length=255)
    description_override: str | None = None
    theme: str = Field(default="light", pattern=r"^(light|dark|auto)$")
    password: str | None = Field(default=None, min_length=6)
    expires_at: datetime | None = None
    allowed_domains: list[str] | None = None


class PublicShareUpdate(BaseModel):
    """Update a public share."""

    show_chart: bool | None = None
    show_components: bool | None = None
    show_performance: bool | None = None
    show_factsheet: bool | None = None
    allow_download: bool | None = None
    title_override: str | None = None
    description_override: str | None = None
    theme: str | None = None
    password: str | None = None
    expires_at: datetime | None = None
    allowed_domains: list[str] | None = None
    is_active: bool | None = None


class PublicShareResponse(BaseModel):
    """Response for public share."""

    id: str
    index_id: str
    slug: str
    show_chart: bool
    show_components: bool
    show_performance: bool
    show_factsheet: bool
    allow_download: bool
    title_override: str | None
    description_override: str | None
    theme: str
    is_active: bool
    has_password: bool
    expires_at: datetime | None
    allowed_domains: list[str] | None
    view_count: int
    last_viewed_at: datetime | None
    created_at: datetime
    public_url: str | None = None  # Computed in API

    class Config:
        from_attributes = True


# Embed Widget Schemas
class EmbedWidgetCreate(BaseModel):
    """Create an embed widget."""

    index_id: str
    name: str = Field(..., min_length=1, max_length=255)
    widget_type: str = Field(
        default="chart", pattern=r"^(chart|table|factsheet|performance|components)$"
    )
    width: str = Field(default="100%", max_length=20)
    height: str = Field(default="400px", max_length=20)
    theme: str = Field(default="light", pattern=r"^(light|dark|auto)$")
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    background_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    font_family: str | None = Field(default=None, max_length=100)
    hide_branding: bool = False
    chart_type: str = Field(default="line", pattern=r"^(line|area|candlestick)$")
    show_volume: bool = False
    show_legend: bool = True
    default_period: str = Field(default="1Y", pattern=r"^(1M|3M|6M|1Y|5Y|ALL)$")
    allowed_domains: list[str] | None = None


class EmbedWidgetUpdate(BaseModel):
    """Update an embed widget."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    widget_type: str | None = None
    width: str | None = None
    height: str | None = None
    theme: str | None = None
    primary_color: str | None = None
    background_color: str | None = None
    font_family: str | None = None
    hide_branding: bool | None = None
    chart_type: str | None = None
    show_volume: bool | None = None
    show_legend: bool | None = None
    default_period: str | None = None
    allowed_domains: list[str] | None = None
    is_active: bool | None = None


class EmbedWidgetResponse(BaseModel):
    """Response for embed widget."""

    id: str
    index_id: str
    name: str
    widget_type: str
    embed_token: str
    width: str
    height: str
    theme: str
    primary_color: str | None
    background_color: str | None
    font_family: str | None
    hide_branding: bool
    chart_type: str
    show_volume: bool
    show_legend: bool
    default_period: str
    is_active: bool
    allowed_domains: list[str] | None
    embed_count: int
    last_embedded_at: datetime | None
    created_at: datetime
    embed_code: str | None = None  # Computed in API

    class Config:
        from_attributes = True
