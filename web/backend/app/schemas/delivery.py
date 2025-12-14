"""
Schemas for data delivery (webhooks, SFTP, email).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, EmailStr


# Webhook Schemas
class WebhookCreate(BaseModel):
    """Create a webhook endpoint."""
    
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=10)
    secret_key: str | None = Field(default=None, max_length=255)
    headers: dict[str, str] | None = None
    events: list[str] = Field(default=["index_update", "rebalance", "corporate_action"])
    index_ids: list[str] | None = None
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)


class WebhookUpdate(BaseModel):
    """Update a webhook endpoint."""
    
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=10)
    secret_key: str | None = None
    headers: dict[str, str] | None = None
    events: list[str] | None = None
    index_ids: list[str] | None = None
    is_active: bool | None = None
    max_retries: int | None = Field(default=None, ge=0, le=10)


class WebhookResponse(BaseModel):
    """Response for webhook endpoint."""
    
    id: str
    name: str
    url: str
    events: list[str]
    index_ids: list[str] | None
    is_active: bool
    max_retries: int
    total_deliveries: int
    successful_deliveries: int
    last_triggered_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_error: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class WebhookTest(BaseModel):
    """Test a webhook endpoint."""
    
    webhook_id: str


# SFTP Schemas
class SFTPCreate(BaseModel):
    """Create an SFTP destination."""
    
    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str | None = Field(default=None, max_length=255)
    private_key: str | None = None
    remote_path: str = Field(default="/", max_length=500)
    frequency: str = Field(default="daily")
    schedule_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    schedule_day: int | None = Field(default=None, ge=0, le=31)
    index_ids: list[str] | None = None
    file_format: str = Field(default="csv", pattern=r"^(csv|json|xlsx)$")
    include_history: bool = False


class SFTPUpdate(BaseModel):
    """Update an SFTP destination."""
    
    name: str | None = Field(default=None, min_length=1, max_length=255)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    remote_path: str | None = None
    frequency: str | None = None
    schedule_time: str | None = None
    schedule_day: int | None = None
    index_ids: list[str] | None = None
    file_format: str | None = None
    include_history: bool | None = None
    is_active: bool | None = None


class SFTPResponse(BaseModel):
    """Response for SFTP destination."""
    
    id: str
    name: str
    host: str
    port: int
    username: str
    remote_path: str
    frequency: str
    schedule_time: str | None
    schedule_day: int | None
    index_ids: list[str] | None
    file_format: str
    include_history: bool
    is_active: bool
    last_delivery_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Email Schemas
class EmailSubscriptionCreate(BaseModel):
    """Create an email subscription."""
    
    name: str = Field(..., min_length=1, max_length=255)
    recipients: list[EmailStr] = Field(..., min_length=1)
    frequency: str = Field(default="weekly")
    schedule_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    schedule_day: int | None = Field(default=None, ge=0, le=31)
    index_ids: list[str] | None = None
    report_type: str = Field(default="factsheet")
    include_attachments: bool = True


class EmailSubscriptionUpdate(BaseModel):
    """Update an email subscription."""
    
    name: str | None = Field(default=None, min_length=1, max_length=255)
    recipients: list[EmailStr] | None = None
    frequency: str | None = None
    schedule_time: str | None = None
    schedule_day: int | None = None
    index_ids: list[str] | None = None
    report_type: str | None = None
    include_attachments: bool | None = None
    is_active: bool | None = None


class EmailSubscriptionResponse(BaseModel):
    """Response for email subscription."""
    
    id: str
    name: str
    recipients: list[str]
    frequency: str
    schedule_time: str | None
    schedule_day: int | None
    index_ids: list[str] | None
    report_type: str
    include_attachments: bool
    is_active: bool
    last_sent_at: datetime | None
    last_error: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Delivery Log
class DeliveryLogResponse(BaseModel):
    """Response for delivery log entry."""
    
    id: str
    delivery_type: str
    destination_id: str
    status: str
    payload_summary: str | None
    file_name: str | None
    file_size_bytes: int | None
    response_code: int | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    attempt_number: int
    
    class Config:
        from_attributes = True

