"""Webhook delivery and stored-credential encryption."""

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.config import settings
from app.models.delivery import DeliveryLog, SFTPDestination, WebhookEndpoint
from app.models.index import Index, IndexComponent
from app.models.user import User
from app.services import delivery_service


class Outbox(list):
    """Captured requests, plus the status the fake receiver answers with."""

    state: dict[str, int]


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    """Capture outbound webhook requests instead of sending them."""
    sent = Outbox()
    state = {"status": 200}
    sent.state = state

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        async def post(self, url: str, content: str, headers: dict[str, str]) -> httpx.Response:
            sent.append(
                {"url": url, "body": json.loads(content), "raw": content, "headers": headers}
            )
            return httpx.Response(state["status"], text="ok")

    monkeypatch.setattr(delivery_service.httpx, "AsyncClient", FakeClient)

    async def allow(url: str) -> None:
        return None

    monkeypatch.setattr(delivery_service, "assert_safe_webhook_url", allow)
    return sent


async def make_index(db: AsyncSession, owner: User) -> Index:
    index = Index(
        owner_id=owner.id,
        name="Hooked",
        identifier="HOOKED",
        base_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        base_value=1000.0,
        divisor=1.0,
        current_value=1000.0,
    )
    db.add(index)
    await db.flush()
    db.add_all(
        [
            IndexComponent(index_id=index.id, ticker="AAA", price=60.0, shares=10.0, weight=0.6),
            IndexComponent(index_id=index.id, ticker="BBB", price=40.0, shares=10.0, weight=0.4),
        ]
    )
    await db.commit()
    return index


async def make_webhook(db: AsyncSession, owner: User, **extra: Any) -> WebhookEndpoint:
    webhook = WebhookEndpoint(
        owner_id=owner.id,
        name="hook",
        url="https://hooks.example.com/in",
        secret_key="s3cret",
        events=["rebalance", "index_update"],
        **extra,
    )
    db.add(webhook)
    await db.commit()
    return webhook


@pytest.fixture
async def pro_user(test_user: User, db_session: AsyncSession) -> User:
    test_user.tier = "pro"
    await db_session.commit()
    return test_user


class TestWebhookDispatch:
    async def test_rebalance_fires_a_signed_webhook(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession, outbox
    ):
        index = await make_index(db_session, pro_user)
        webhook = await make_webhook(db_session, pro_user)

        response = await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)
        assert response.status_code == 200

        assert len(outbox) == 1
        request = outbox[0]
        assert request["url"] == "https://hooks.example.com/in"
        assert request["body"]["event"] == "rebalance"
        assert request["body"]["data"]["identifier"] == "HOOKED"
        assert {c["ticker"] for c in request["body"]["data"]["constituents"]} == {"AAA", "BBB"}
        # The receiver can verify the body came from us.
        assert request["headers"]["X-Webhook-Signature"] == delivery_service.sign_payload(
            "s3cret", request["raw"]
        )

        assert webhook.total_deliveries == 1 and webhook.successful_deliveries == 1
        logs = (await db_session.execute(select(DeliveryLog))).scalars().all()
        assert [(log.status, log.payload_summary) for log in logs] == [("success", "rebalance")]

    async def test_recalculation_fires_index_update(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession, outbox
    ):
        index = await make_index(db_session, pro_user)
        await make_webhook(db_session, pro_user)
        response = await client.post(f"/api/v1/indices/{index.id}/calculate", headers=auth_headers)
        assert response.status_code == 200
        assert [r["body"]["event"] for r in outbox] == ["index_update"]

    async def test_only_subscribed_events_and_indices_are_sent(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession, outbox
    ):
        index = await make_index(db_session, pro_user)
        other = await make_webhook(db_session, pro_user, index_ids=["some-other-index"])
        other.events = ["rebalance"]
        paused = await make_webhook(db_session, pro_user, is_active=False)
        assert paused.is_active is False
        await db_session.commit()

        await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)
        assert outbox == []

    async def test_a_failing_receiver_does_not_fail_the_rebalance(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession, outbox
    ):
        outbox.state["status"] = 500
        index = await make_index(db_session, pro_user)
        webhook = await make_webhook(db_session, pro_user)

        response = await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)
        assert response.status_code == 200
        assert webhook.successful_deliveries == 0
        assert webhook.last_error == "HTTP 500"

    async def test_free_accounts_do_not_deliver(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, outbox
    ):
        index = await make_index(db_session, test_user)
        await make_webhook(db_session, test_user)
        await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)
        assert outbox == []

    async def test_test_button_uses_the_same_sender(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession, outbox
    ):
        webhook = await make_webhook(db_session, pro_user)
        response = await client.post(
            f"/api/v1/delivery/webhooks/{webhook.id}/test", headers=auth_headers
        )
        assert response.json()["success"] is True
        assert outbox[0]["body"]["event"] == "test"


class TestWebhookURLSafety:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/hook",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.5/internal",
            "ftp://example.com/x",
            "not a url",
        ],
    )
    async def test_private_and_malformed_urls_are_refused(self, url: str, monkeypatch):
        monkeypatch.setattr(settings, "DEBUG", False)
        with pytest.raises(delivery_service.UnsafeWebhookURLError):
            await delivery_service.assert_safe_webhook_url(url)

    async def test_create_rejects_an_internal_url(
        self, client: AsyncClient, auth_headers, pro_user: User, monkeypatch
    ):
        monkeypatch.setattr(settings, "DEBUG", False)
        response = await client.post(
            "/api/v1/delivery/webhooks",
            headers=auth_headers,
            json={"name": "sneaky", "url": "http://127.0.0.1:6379/"},
        )
        assert response.status_code == 422


class TestCredentialEncryption:
    def test_round_trip_and_legacy_plaintext(self):
        stored = crypto.encrypt_secret("hunter2")
        assert stored != "hunter2" and stored.startswith("enc:v1:")
        assert crypto.decrypt_secret(stored) == "hunter2"
        # Encrypting twice must not double-wrap.
        assert crypto.encrypt_secret(stored) == stored
        # Rows written before encryption existed still read back.
        assert crypto.decrypt_secret("old-plaintext") == "old-plaintext"
        assert crypto.encrypt_secret(None) is None

    def test_wrong_key_is_a_clear_error(self, monkeypatch):
        stored = crypto.encrypt_secret("hunter2")
        monkeypatch.setattr(settings, "SECRET_KEY", "a-different-key")
        with pytest.raises(crypto.SecretDecryptionError):
            crypto.decrypt_secret(stored)

    async def test_sftp_password_is_not_stored_in_the_clear(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession
    ):
        response = await client.post(
            "/api/v1/delivery/sftp",
            headers=auth_headers,
            json={
                "name": "drop",
                "host": "sftp.example.com",
                "username": "u",
                "password": "hunter2",
            },
        )
        assert response.status_code == 201
        assert "password" not in response.json()

        row = (await db_session.execute(select(SFTPDestination))).scalar_one()
        assert row.password != "hunter2"
        assert crypto.decrypt_secret(row.password) == "hunter2"
