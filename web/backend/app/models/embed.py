"""
Embeddable Widget Models.

Handles public sharing and iframe embedding of indices.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EmbedType(str, Enum):
    """Types of embeddable widgets."""

    CHART = "chart"
    TABLE = "table"
    FACTSHEET = "factsheet"
    PERFORMANCE = "performance"
    COMPONENTS = "components"


class EmbedTheme(str, Enum):
    """Visual themes for embeds."""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class PublicShare(Base):
    """
    Public share link for an index.
    Allows viewing without authentication.
    """

    __tablename__ = "public_shares"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # The index being shared
    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("indices.id"), nullable=False
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )

    # Unique slug for the public URL
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # What to show
    show_chart: Mapped[bool] = mapped_column(Boolean, default=True)
    show_components: Mapped[bool] = mapped_column(Boolean, default=True)
    show_performance: Mapped[bool] = mapped_column(Boolean, default=True)
    show_factsheet: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_download: Mapped[bool] = mapped_column(Boolean, default=False)

    # Customization
    title_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    theme: Mapped[str] = mapped_column(String(20), default=EmbedTheme.LIGHT.value)

    # Access control
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allowed_domains: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # For CORS

    # Stats
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="public_shares")
    owner: Mapped["User"] = relationship("User", back_populates="public_shares")

    def __repr__(self) -> str:
        return f"<PublicShare {self.slug}>"


class EmbedWidget(Base):
    """
    Configurable embeddable widget for an index.
    Generates iframe embed code.
    """

    __tablename__ = "embed_widgets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("indices.id"), nullable=False
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    widget_type: Mapped[str] = mapped_column(String(20), default=EmbedType.CHART.value)

    # Embed token for authentication
    embed_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Dimensions
    width: Mapped[str] = mapped_column(String(20), default="100%")
    height: Mapped[str] = mapped_column(String(20), default="400px")

    # Styling
    theme: Mapped[str] = mapped_column(String(20), default=EmbedTheme.LIGHT.value)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # Hex color
    background_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    font_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hide_branding: Mapped[bool] = mapped_column(Boolean, default=False)  # Premium feature

    # Chart options
    chart_type: Mapped[str] = mapped_column(String(20), default="line")  # line, area, candlestick
    show_volume: Mapped[bool] = mapped_column(Boolean, default=False)
    show_legend: Mapped[bool] = mapped_column(Boolean, default=True)
    default_period: Mapped[str] = mapped_column(String(10), default="1Y")  # 1M, 3M, 6M, 1Y, 5Y, ALL

    # Access control
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_domains: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Stats
    embed_count: Mapped[int] = mapped_column(Integer, default=0)
    last_embedded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="embed_widgets")
    owner: Mapped["User"] = relationship("User", back_populates="embed_widgets")

    def get_embed_code(self, base_url: str) -> str:
        """Generate the iframe embed code."""
        return f'<iframe src="{base_url}/embed/{self.embed_token}" width="{self.width}" height="{self.height}" frameborder="0" allowtransparency="true"></iframe>'

    def __repr__(self) -> str:
        return f"<EmbedWidget {self.name} ({self.widget_type})>"
