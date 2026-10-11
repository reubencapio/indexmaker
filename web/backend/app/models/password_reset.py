"""
Password Reset Token model.

Stores secure tokens for password reset functionality.
"""

import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def generate_reset_token() -> str:
    """Generate a cryptographically secure reset token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return sha256(token.encode()).hexdigest()


class PasswordResetToken(Base):
    """
    Password reset token for forgot password functionality.

    Tokens are stored as hashes for security.
    Each token can only be used once and expires after 1 hour.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    # Same type as users.id: Postgres refuses a foreign key between a varchar
    # and a uuid column, so the previous String(36) could never be created.
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=1),
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user = relationship("User")

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid (not expired and not used)."""
        return self.used_at is None and self.expires_at > datetime.now(timezone.utc)

    def mark_used(self) -> None:
        """Mark the token as used."""
        self.used_at = datetime.now(timezone.utc)
