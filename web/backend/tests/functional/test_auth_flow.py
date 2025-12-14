"""
Functional tests for authentication flow.

Tests the complete authentication workflow including:
- User registration
- Login
- Token refresh
- Protected route access
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthFlow:
    """Test complete authentication flow."""

    async def test_register_login_flow(self, client: AsyncClient):
        """Test user can register and then login."""
        # Register new user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == "newuser@example.com"
        assert user_data["full_name"] == "New User"
        assert "id" in user_data

        # Login with new credentials
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login fails with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration fails with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "somepassword",
                "full_name": "Duplicate User",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_protected_route_without_token(self, client: AsyncClient):
        """Test protected route returns 401 without token."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_protected_route_with_token(self, client: AsyncClient, test_user, auth_headers):
        """Test protected route works with valid token."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["email"] == test_user.email

    async def test_token_refresh(self, client: AsyncClient, test_user):
        """Test token refresh flow."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword",
            },
        )
        tokens = login_response.json()

        # Refresh the token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

    async def test_invalid_refresh_token(self, client: AsyncClient):
        """Test refresh fails with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401
