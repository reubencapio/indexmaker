"""
Report and Factsheet Models.

Handles PDF generation and report templates.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ReportType(str, Enum):
    """Types of reports."""
    
    FACTSHEET = "factsheet"
    PERFORMANCE = "performance"
    COMPONENTS = "components"
    FULL = "full"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Output formats for reports."""
    
    PDF = "pdf"
    HTML = "html"
    XLSX = "xlsx"


class ReportStatus(str, Enum):
    """Status of report generation."""
    
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportTemplate(Base):
    """
    Customizable report template.
    """
    
    __tablename__ = "report_templates"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True  # null = system template
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(
        String(20), default=ReportType.FACTSHEET.value
    )
    
    # Template structure
    is_system_template: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Header customization
    show_logo: Mapped[bool] = mapped_column(Boolean, default=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    header_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    footer_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Sections to include
    sections: Mapped[dict[str, Any]] = mapped_column(JSON, default={
        "summary": True,
        "performance_chart": True,
        "performance_table": True,
        "risk_metrics": True,
        "top_components": True,
        "all_components": False,
        "sector_breakdown": True,
        "country_breakdown": True,
        "methodology": True,
        "disclaimer": True,
    })
    
    # Styling
    primary_color: Mapped[str] = mapped_column(String(7), default="#1a56db")
    secondary_color: Mapped[str] = mapped_column(String(7), default="#6b7280")
    font_family: Mapped[str] = mapped_column(String(100), default="Inter, sans-serif")
    
    # Custom CSS (for advanced users)
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="report_templates")
    
    def __repr__(self) -> str:
        return f"<ReportTemplate {self.name}>"


class GeneratedReport(Base):
    """
    A generated report instance.
    """
    
    __tablename__ = "generated_reports"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    
    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("indices.id"), nullable=False
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("report_templates.id"), nullable=True
    )
    
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    report_format: Mapped[str] = mapped_column(
        String(10), default=ReportFormat.PDF.value
    )
    
    # Report period
    as_of_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20), default=ReportStatus.PENDING.value
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Generated file
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata from generation
    metrics_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    # Access
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="generated_reports")
    owner: Mapped["User"] = relationship("User", back_populates="generated_reports")
    template: Mapped["ReportTemplate"] = relationship("ReportTemplate")
    
    def __repr__(self) -> str:
        return f"<GeneratedReport {self.report_type} for {self.index_id}>"

