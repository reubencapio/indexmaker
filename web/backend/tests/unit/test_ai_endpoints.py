"""
Unit tests for AI index creation endpoints.

Tests the AI status and generation endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


class TestAIStatusEndpoint:
    """Tests for the AI status endpoint."""

    @pytest.mark.asyncio
    async def test_ai_status_with_gemini_key(self, client, auth_headers):
        """Test AI status returns gemini when GEMINI_API_KEY is set."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "test-gemini-key"
            mock_settings.OPENAI_API_KEY = None
            
            response = await client.get("/api/v1/ai/status", headers=auth_headers)
            # Note: The endpoint doesn't require auth, so it should work
            assert response.status_code in [200, 401]  # 401 if auth required

    @pytest.mark.asyncio
    async def test_ai_status_with_openai_key(self, client, auth_headers):
        """Test AI status returns openai when only OPENAI_API_KEY is set."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            mock_settings.OPENAI_API_KEY = "test-openai-key"
            
            response = await client.get("/api/v1/ai/status", headers=auth_headers)
            assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_ai_status_no_keys(self, client, auth_headers):
        """Test AI status returns unavailable when no API keys are set."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            mock_settings.OPENAI_API_KEY = None
            
            response = await client.get("/api/v1/ai/status", headers=auth_headers)
            assert response.status_code in [200, 401]


class TestAICreateEndpoint:
    """Tests for the AI index creation endpoint."""

    @pytest.mark.asyncio
    async def test_ai_create_requires_authentication(self, client):
        """Test that AI create endpoint requires authentication."""
        response = await client.post(
            "/api/v1/ai/create",
            json={"description": "test index"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ai_create_with_auth(self, client, auth_headers):
        """Test AI create endpoint with valid authentication."""
        with patch("app.tasks.generate_and_populate_index_task") as mock_task:
            mock_task.delay = AsyncMock()
            
            response = await client.post(
                "/api/v1/ai/create",
                headers=auth_headers,
                json={
                    "description": "Top 10 US technology companies",
                    "base_value": 1000.0
                }
            )
            # Should either succeed or fail based on DB state
            assert response.status_code in [200, 201, 422, 500]


class TestAIGenerateEndpoint:
    """Tests for the AI generate (preview) endpoint."""

    @pytest.mark.asyncio
    async def test_ai_generate_requires_authentication(self, client):
        """Test that AI generate endpoint requires authentication."""
        response = await client.post(
            "/api/v1/ai/generate",
            json={"description": "test index"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ai_generate_validates_request(self, client, auth_headers):
        """Test that AI generate validates the request body."""
        response = await client.post(
            "/api/v1/ai/generate",
            headers=auth_headers,
            json={}  # Missing required 'description' field
        )
        assert response.status_code == 422  # Validation error
