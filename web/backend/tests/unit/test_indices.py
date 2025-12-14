"""
Unit tests for index endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestIndexEndpoints:
    """Test index CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_index(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test creating a new index."""
        response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "My Test Index",
                "identifier": "TESTIDX",
                "description": "A test index",
                "currency": "USD",
                "weighting_method": "equal_weight",
                "rebalance_frequency": "quarterly",
                "base_date": "2024-01-01T00:00:00Z",
                "base_value": 1000.0,
                "max_components": 50,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Test Index"
        assert data["identifier"] == "TESTIDX"
        assert data["owner_id"] == test_user.id
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_index_with_components(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test creating an index with initial components."""
        response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "Tech Index",
                "identifier": "TECHIDX",
                "base_date": "2024-01-01T00:00:00Z",
                "components": [
                    {"ticker": "AAPL", "weight": 0.25},
                    {"ticker": "MSFT", "weight": 0.25},
                    {"ticker": "GOOGL", "weight": 0.25},
                    {"ticker": "AMZN", "weight": 0.25},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["components"]) == 4

    @pytest.mark.asyncio
    async def test_create_index_duplicate_identifier(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test creating index with duplicate identifier."""
        # Create first index
        await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "First Index",
                "identifier": "DUPIDX",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )

        # Try to create duplicate
        response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "Second Index",
                "identifier": "DUPIDX",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_index_no_auth(self, client: AsyncClient):
        """Test creating index without authentication."""
        response = await client.post(
            "/api/v1/indices/",
            json={
                "name": "Unauthorized Index",
                "identifier": "NOAUTH",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_own_indices(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test listing user's own indices."""
        # Create an index first
        await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "List Test Index",
                "identifier": "LISTIDX",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )

        response = await client.get(
            "/api/v1/indices/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_index(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting a specific index."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "Get Test Index",
                "identifier": "GETIDX",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )
        index_id = create_response.json()["id"]

        # Get index
        response = await client.get(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["id"] == index_id

    @pytest.mark.asyncio
    async def test_update_index(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test updating an index."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "Update Test Index",
                "identifier": "UPDIDX",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )
        index_id = create_response.json()["id"]

        # Update index
        response = await client.patch(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
            json={
                "name": "Updated Index Name",
                "description": "New description",
            },
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Index Name"
        assert response.json()["description"] == "New description"

    @pytest.mark.asyncio
    async def test_delete_index(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting an index."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "Delete Test Index",
                "identifier": "DELIDX",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )
        index_id = create_response.json()["id"]

        # Delete index
        response = await client.delete(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_component(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test adding a component to an index."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "Component Test Index",
                "identifier": "COMPIDX",
                "base_date": "2024-01-01T00:00:00Z",
            },
        )
        index_id = create_response.json()["id"]

        # Add component
        response = await client.post(
            f"/api/v1/indices/{index_id}/components",
            headers=auth_headers,
            json={
                "ticker": "AAPL",
                "weight": 0.1,
            },
        )

        assert response.status_code == 200
        assert response.json()["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_remove_component(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test removing a component from an index."""
        # Create index with component
        create_response = await client.post(
            "/api/v1/indices/",
            headers=auth_headers,
            json={
                "name": "Remove Component Index",
                "identifier": "RMCOMPIDX",
                "base_date": "2024-01-01T00:00:00Z",
                "components": [{"ticker": "AAPL", "weight": 0.5}],
            },
        )
        index_id = create_response.json()["id"]

        # Remove component
        response = await client.delete(
            f"/api/v1/indices/{index_id}/components/AAPL",
            headers=auth_headers,
        )

        assert response.status_code == 204
