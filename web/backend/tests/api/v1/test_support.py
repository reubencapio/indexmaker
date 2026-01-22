import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_contact_support(client: AsyncClient):
    data = {
        "name": "Test User",
        "email": "test@example.com",
        "subject": "Test Subject",
        "message": "This is a test message",
    }
    response = await client.post(
        "/api/v1/support/contact",
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["status"] == "success"
    assert content["message"] == "Support request received"


@pytest.mark.asyncio
async def test_contact_support_invalid_email(client: AsyncClient):
    data = {
        "name": "Test User",
        "email": "invalid-email",
        "subject": "Test Subject",
        "message": "This is a test message",
    }
    response = await client.post(
        "/api/v1/support/contact",
        json=data,
    )
    assert response.status_code == 422
