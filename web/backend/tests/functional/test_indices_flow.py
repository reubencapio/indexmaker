"""
Functional tests for index management flow.

Tests the complete index workflow including:
- Creating indices
- Listing indices
- Updating indices
- Adding components
- Deleting indices
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestIndicesFlow:
    """Test complete index management flow."""

    async def test_create_and_list_index(self, client: AsyncClient, auth_headers):
        """Test creating an index and listing it."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices",
            headers=auth_headers,
            json={
                "name": "Test Index",
                "identifier": "TESTIDX",
                "description": "A test index",
                "currency": "USD",
                "base_date": "2024-01-01",
                "base_value": 1000,
                "weighting_method": "equal",
            },
        )
        assert create_response.status_code == 201
        index = create_response.json()
        assert index["name"] == "Test Index"
        assert index["identifier"] == "TESTIDX"
        index_id = index["id"]

        # List indices
        list_response = await client.get(
            "/api/v1/indices",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        indices = list_response.json()
        assert len(indices) >= 1
        assert any(idx["id"] == index_id for idx in indices)

    async def test_get_index_detail(self, client: AsyncClient, auth_headers):
        """Test getting index details."""
        # Create index first
        create_response = await client.post(
            "/api/v1/indices",
            headers=auth_headers,
            json={
                "name": "Detail Test Index",
                "identifier": "DTESTIDX",
                "base_date": "2024-01-01",
            },
        )
        index_id = create_response.json()["id"]

        # Get details
        detail_response = await client.get(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
        )
        assert detail_response.status_code == 200
        index = detail_response.json()
        assert index["id"] == index_id
        assert index["name"] == "Detail Test Index"

    async def test_update_index(self, client: AsyncClient, auth_headers):
        """Test updating an index."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices",
            headers=auth_headers,
            json={
                "name": "Update Test Index",
                "identifier": "UPDTIDX",
                "base_date": "2024-01-01",
            },
        )
        index_id = create_response.json()["id"]

        # Update index
        update_response = await client.patch(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
            json={
                "name": "Updated Index Name",
                "description": "Updated description",
            },
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "Updated Index Name"
        assert updated["description"] == "Updated description"

    async def test_add_component_to_index(self, client: AsyncClient, auth_headers):
        """Test adding a component to an index."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices",
            headers=auth_headers,
            json={
                "name": "Component Test Index",
                "identifier": "CMPIDX",
                "base_date": "2024-01-01",
            },
        )
        index_id = create_response.json()["id"]

        # Add component
        add_response = await client.post(
            f"/api/v1/indices/{index_id}/components",
            headers=auth_headers,
            json={
                "ticker": "AAPL",
                "weight": 0.25,
            },
        )
        assert add_response.status_code in [200, 201]

        # Verify component was added
        detail_response = await client.get(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
        )
        index = detail_response.json()
        assert index["component_count"] >= 1

    async def test_delete_index(self, client: AsyncClient, auth_headers):
        """Test deleting an index."""
        # Create index
        create_response = await client.post(
            "/api/v1/indices",
            headers=auth_headers,
            json={
                "name": "Delete Test Index",
                "identifier": "DELIDX",
                "base_date": "2024-01-01",
            },
        )
        index_id = create_response.json()["id"]

        # Delete index
        delete_response = await client.delete(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Verify deletion
        get_response = await client.get(
            f"/api/v1/indices/{index_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_unauthorized_access(self, client: AsyncClient):
        """Test index endpoints require authentication."""
        # List without auth
        response = await client.get("/api/v1/indices")
        assert response.status_code == 401

        # Create without auth
        response = await client.post(
            "/api/v1/indices",
            json={
                "name": "Unauthorized Index",
                "identifier": "UNAUTH",
                "base_date": "2024-01-01",
            },
        )
        assert response.status_code == 401

    async def test_index_not_found(self, client: AsyncClient, auth_headers):
        """Test accessing non-existent index."""
        response = await client.get(
            "/api/v1/indices/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


