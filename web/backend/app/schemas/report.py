"""
Schemas for reports and factsheets.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# Report Template Schemas
class ReportTemplateCreate(BaseModel):
    """Create a report template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    report_type: str = Field(default="factsheet")
    show_logo: bool = True
    logo_url: str | None = None
    header_text: str | None = Field(default=None, max_length=255)
    footer_text: str | None = Field(default=None, max_length=255)
    sections: dict[str, bool] | None = None
    primary_color: str = Field(default="#1a56db", pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str = Field(default="#6b7280", pattern=r"^#[0-9a-fA-F]{6}$")
    font_family: str = Field(default="Inter, sans-serif", max_length=100)
    custom_css: str | None = None


class ReportTemplateUpdate(BaseModel):
    """Update a report template."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    show_logo: bool | None = None
    logo_url: str | None = None
    header_text: str | None = None
    footer_text: str | None = None
    sections: dict[str, bool] | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    font_family: str | None = None
    custom_css: str | None = None


class ReportTemplateResponse(BaseModel):
    """Response for report template."""

    id: str
    owner_id: str | None
    name: str
    description: str | None
    report_type: str
    is_system_template: bool
    show_logo: bool
    logo_url: str | None
    header_text: str | None
    footer_text: str | None
    sections: dict[str, Any]
    primary_color: str
    secondary_color: str
    font_family: str
    created_at: datetime

    class Config:
        from_attributes = True


# Generated Report Schemas
class GenerateReportRequest(BaseModel):
    """Request to generate a report."""

    index_id: str
    template_id: str | None = None
    report_type: str = Field(default="factsheet")
    report_format: str = Field(default="pdf", pattern=r"^(pdf|html|xlsx)$")
    as_of_date: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    is_public: bool = False


class GeneratedReportResponse(BaseModel):
    """Response for generated report."""

    id: str
    index_id: str
    template_id: str | None
    report_type: str
    report_format: str
    as_of_date: datetime
    period_start: datetime | None
    period_end: datetime | None
    status: str
    error_message: str | None
    file_path: str | None
    file_size_bytes: int | None
    file_url: str | None
    is_public: bool
    public_token: str | None
    download_count: int
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


# Performance metrics for reports
class PerformanceMetrics(BaseModel):
    """Performance metrics included in reports."""

    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    current_value: float
    ytd_return: float
    mtd_return: float
    one_year_return: float | None
    three_year_return: float | None
    five_year_return: float | None
    since_inception_return: float
