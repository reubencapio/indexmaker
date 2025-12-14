"""
Integration tests for database operations.

Tests database connectivity and model operations.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestDatabaseConnection:
    """Test database connectivity."""

    async def test_database_connection(self, db_session: AsyncSession):
        """Test database is connected and responsive."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_tables_exist(self, db_session: AsyncSession):
        """Test that all required tables exist."""
        # Check users table
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            )
        )
        assert result.scalar() is True

        # Check indices table
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'indices')"
            )
        )
        assert result.scalar() is True


@pytest.mark.asyncio
class TestUserModel:
    """Test User model operations."""

    async def test_create_user(self, db_session: AsyncSession, test_user):
        """Test user creation."""
        assert test_user.id is not None
        assert test_user.email == "test@example.com"
        assert test_user.is_active is True

    async def test_user_has_password_hash(self, test_user):
        """Test user password is hashed."""
        assert test_user.hashed_password is not None
        assert test_user.hashed_password != "testpassword"
        assert test_user.hashed_password.startswith("$2b$")

