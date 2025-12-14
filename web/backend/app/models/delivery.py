"""
Delivery Models.

Handles webhook notifications, SFTP delivery, and email reports.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DeliveryType(str, Enum):
    """Types of data delivery."""
    
    WEBHOOK = "webhook"
    SFTP = "sftp"
    EMAIL = "email"


class DeliveryFrequency(str, Enum):
    """Frequency of scheduled deliveries."""
    
    REALTIME = "realtime"  # On every index update
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DeliveryStatus(str, Enum):
    """Status of a delivery attempt."""
    
    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookEndpoint(Base):
    """
    User-configured webhook endpoint for receiving index updates.
    """
    
    __tablename__ = "webhook_endpoints"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Authentication
    secret_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headers: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    
    # What to send
    events: Mapped[list[str]] = mapped_column(
        JSON, default=["index_update", "rebalance", "corporate_action"]
    )
    
    # Which indices to watch (null = all user's indices)
    index_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Retry configuration
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60)
    
    # Stats
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    successful_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="webhook_endpoints")
    
    def __repr__(self) -> str:
        return f"<WebhookEndpoint {self.name} -> {self.url}>"


class SFTPDestination(Base):
    """
    SFTP destination for scheduled file delivery.
    """
    
    __tablename__ = "sftp_destinations"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=22)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Encrypted
    private_key: Mapped[str | None] = mapped_column(Text, nullable=True)  # Encrypted
    remote_path: Mapped[str] = mapped_column(String(500), default="/")
    
    # Schedule
    frequency: Mapped[str] = mapped_column(
        String(20), default=DeliveryFrequency.DAILY.value
    )
    schedule_time: Mapped[str | None] = mapped_column(String(10), nullable=True)  # HH:MM format
    schedule_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Day of week/month
    
    # What to deliver
    index_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    file_format: Mapped[str] = mapped_column(String(20), default="csv")  # csv, json, xlsx
    include_history: Mapped[bool] = mapped_column(Boolean, default=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Stats
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="sftp_destinations")
    
    def __repr__(self) -> str:
        return f"<SFTPDestination {self.name} -> {self.host}>"


class EmailSubscription(Base):
    """
    Email subscription for scheduled reports.
    """
    
    __tablename__ = "email_subscriptions"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipients: Mapped[list[str]] = mapped_column(JSON, nullable=False)  # List of emails
    
    # Schedule
    frequency: Mapped[str] = mapped_column(
        String(20), default=DeliveryFrequency.WEEKLY.value
    )
    schedule_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    schedule_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # What to send
    index_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), default="factsheet")  # factsheet, performance, full
    include_attachments: Mapped[bool] = mapped_column(Boolean, default=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Stats
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="email_subscriptions")
    
    def __repr__(self) -> str:
        return f"<EmailSubscription {self.name}>"


class DeliveryLog(Base):
    """
    Log of all delivery attempts.
    """
    
    __tablename__ = "delivery_logs"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    
    delivery_type: Mapped[str] = mapped_column(String(20), nullable=False)
    destination_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    
    status: Mapped[str] = mapped_column(
        String(20), default=DeliveryStatus.PENDING.value
    )
    
    # What was sent
    payload_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Result
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Retry info
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    
    def __repr__(self) -> str:
        return f"<DeliveryLog {self.delivery_type} {self.status}>"

