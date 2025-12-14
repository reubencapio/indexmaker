"""
User schemas for API validation.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for user profile update."""

    full_name: str | None = None
    password: str | None = Field(None, min_length=8, max_length=100)


class UserResponse(UserBase):
    """Schema for user response."""

    id: str
    role: str
    tier: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    """Schema for user in database (includes hashed password)."""

    id: str
    hashed_password: str
    role: str
    tier: str
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True
