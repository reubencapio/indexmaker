"""
User model for authentication and authorization.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.plans import get_plan
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.data_source import CustomDataSource
    from app.models.delivery import EmailSubscription, SFTPDestination, WebhookEndpoint
    from app.models.embed import EmbedWidget, PublicShare
    from app.models.index import Index
    from app.models.report import GeneratedReport, ReportTemplate


class UserRole(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class UserTier(str, Enum):
    """Subscription tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(Base):
    """
    User model for authentication and profile.

    Attributes:
        id: Unique identifier (UUID)
        email: User's email (unique, indexed)
        hashed_password: Bcrypt hashed password
        full_name: User's display name
        role: User role for permissions
        tier: Subscription tier
        is_active: Whether user can login
        is_verified: Whether email is verified
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login: Last successful login
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.USER.value,
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(
        String(50),
        default=UserTier.FREE.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Stripe / Subscription
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "month" or "year": which price the subscription is on.
    subscription_interval: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # When the paid period ends. With cancel_at_period_end set this is the date
    # access lapses; otherwise it is the next renewal.
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relationships
    indices: Mapped[list["Index"]] = relationship(
        "Index",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    data_sources: Mapped[list["CustomDataSource"]] = relationship(
        "CustomDataSource",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    webhook_endpoints: Mapped[list["WebhookEndpoint"]] = relationship(
        "WebhookEndpoint",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    sftp_destinations: Mapped[list["SFTPDestination"]] = relationship(
        "SFTPDestination",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    email_subscriptions: Mapped[list["EmailSubscription"]] = relationship(
        "EmailSubscription",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    public_shares: Mapped[list["PublicShare"]] = relationship(
        "PublicShare",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    embed_widgets: Mapped[list["EmbedWidget"]] = relationship(
        "EmbedWidget",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    report_templates: Mapped[list["ReportTemplate"]] = relationship(
        "ReportTemplate",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    generated_reports: Mapped[list["GeneratedReport"]] = relationship(
        "GeneratedReport",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN.value

    @property
    def max_indices(self) -> int:
        """Maximum indices allowed based on tier."""
        limit = get_plan(self.tier).max_indices
        return limit if limit is not None else 1_000_000
