"""
Unit tests for authentication.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        """Test user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with existing email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "anotherpassword",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting current user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_no_auth(self, client: AsyncClient):
        """Test getting current user without auth."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401  # HTTPBearer returns 401 for missing auth

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user: User):
        """Test token refresh."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestPasswordReset:
    """The forgot / reset password flow, end to end."""

    @pytest.mark.asyncio
    async def test_reset_flow_changes_the_password_and_burns_the_token(
        self, client: AsyncClient, test_user: User, monkeypatch
    ):
        from app.api.v1.endpoints import support

        sent: dict = {}

        def capture(to_email: str, subject: str, html_body: str, text_body: str | None = None):
            sent.update(to=to_email, text=text_body or "")
            return True

        monkeypatch.setattr(support, "send_email", capture)

        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": test_user.email}
        )
        assert response.status_code == 200
        assert sent["to"] == test_user.email
        token = sent["text"].split("reset-password?token=")[1].split()[0]

        response = await client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnewpass1"}
        )
        assert response.status_code == 200

        login = await client.post(
            "/api/v1/auth/login", json={"email": test_user.email, "password": "brandnewpass1"}
        )
        assert login.status_code == 200

        # A reset link works once.
        again = await client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "anotherpass12"}
        )
        assert again.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_email_gets_the_same_answer(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_bad_token_is_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/reset-password", json={"token": "nope", "new_password": "whatever123"}
        )
        assert response.status_code == 400
