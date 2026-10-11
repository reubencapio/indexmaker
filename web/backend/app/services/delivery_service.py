"""
Webhook delivery: tell a customer's systems when one of their indices changes.

Configuring a webhook used to do nothing beyond enabling a "send test" button --
no index event ever reached it. This module is what actually fires them.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.plans import FEATURE_DELIVERY, get_plan
from app.models.delivery import DeliveryLog, DeliveryStatus, WebhookEndpoint
from app.models.index import Index
from app.models.user import User

logger = logging.getLogger(__name__)

EVENT_INDEX_UPDATE = "index_update"
EVENT_REBALANCE = "rebalance"
EVENT_CORPORATE_ACTION = "corporate_action"

# Short on purpose: delivery happens inside the request that caused the event,
# and a slow receiver must not make the user's own action feel slow.
DELIVERY_TIMEOUT_SECONDS = 5.0


class UnsafeWebhookURLError(ValueError):
    """The URL points somewhere the server must not be made to call."""


def _is_public_address(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            return False
    return True


async def assert_safe_webhook_url(url: str) -> None:
    """
    Refuse URLs that would turn the server into a proxy onto its own network.

    A webhook URL is supplied by a customer and requested by us. Without this
    check, "http://169.254.169.254/..." or an internal hostname would let anyone
    with an account read cloud metadata or probe private services.

    Raises:
        UnsafeWebhookURLError: if the URL is not http(s) or resolves privately.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeWebhookURLError("Webhook URL must be an http(s) address.")
    # Local development needs to be able to post to localhost.
    if settings.DEBUG:
        return
    if not await asyncio.to_thread(_is_public_address, parsed.hostname):
        raise UnsafeWebhookURLError("Webhook URL must be a public address.")


def sign_payload(secret: str, body: str) -> str:
    """Hex HMAC-SHA256 of the body, sent as X-Webhook-Signature."""
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def send_webhook(
    db: AsyncSession,
    webhook: WebhookEndpoint,
    event: str,
    data: dict[str, Any],
    *,
    timeout: float = DELIVERY_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Deliver one event to one endpoint, recording the outcome on the endpoint and
    in the delivery log. Never raises: a failed delivery is a result, not an error.
    """
    now = datetime.now(timezone.utc)
    body = json.dumps(
        {"event": event, "timestamp": now.isoformat(), "data": data}, sort_keys=True, default=str
    )
    headers = dict(webhook.headers or {})
    headers["Content-Type"] = "application/json"
    headers["X-Webhook-Event"] = event
    if webhook.secret_key:
        headers["X-Webhook-Signature"] = sign_payload(webhook.secret_key, body)

    status_code: int | None = None
    response_text: str | None = None
    error: str | None = None
    try:
        await assert_safe_webhook_url(webhook.url)
        # No redirects: a public URL must not be able to bounce us to a private one.
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(webhook.url, content=body, headers=headers)
        status_code = response.status_code
        response_text = response.text[:500] if response.text else None
        if not response.is_success:
            error = f"HTTP {status_code}"
    except UnsafeWebhookURLError as exc:
        error = str(exc)
    except httpx.HTTPError as exc:
        error = f"{type(exc).__name__}: {exc}"[:500] or "Request failed"

    success = error is None
    webhook.total_deliveries = (webhook.total_deliveries or 0) + 1
    webhook.last_triggered_at = now
    if success:
        webhook.successful_deliveries = (webhook.successful_deliveries or 0) + 1
        webhook.last_success_at = now
    else:
        webhook.last_failure_at = now
        webhook.last_error = error

    db.add(
        DeliveryLog(
            delivery_type="webhook",
            destination_id=webhook.id,
            status=DeliveryStatus.SUCCESS.value if success else DeliveryStatus.FAILED.value,
            payload_summary=event,
            response_code=status_code,
            response_body=response_text,
            error_message=error,
            completed_at=datetime.now(timezone.utc),
        )
    )
    return {
        "success": success,
        "status_code": status_code,
        "response": response_text,
        "error": error,
    }


def index_payload(index: Index) -> dict[str, Any]:
    """The index as a webhook receiver sees it."""
    return {
        "index_id": index.id,
        "identifier": index.identifier,
        "name": index.name,
        "currency": index.currency,
        "level": index.current_value,
        "calculated_at": index.last_calculated,
        "constituents": [
            {"ticker": c.ticker, "weight": c.weight, "price": c.price, "shares": c.shares}
            for c in index.components
            if c.is_active
        ],
    }


async def dispatch_index_event(db: AsyncSession, index: Index, event: str) -> int:
    """
    Send `event` for `index` to every webhook of its owner that subscribes to it.

    Returns the number of endpoints attempted. Commits the delivery records. Any
    failure here is logged and swallowed: the action that triggered the event has
    already succeeded and must not be reported as failed because a customer's
    receiver is down.
    """
    try:
        owner = await db.get(User, index.owner_id)
        # Delivery is a paid feature; endpoints of a lapsed account stay
        # configured but go quiet until the plan is restored.
        if owner is None or not get_plan(owner.tier).has(FEATURE_DELIVERY):
            return 0

        result = await db.execute(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.owner_id == index.owner_id)
            .where(WebhookEndpoint.is_active == True)  # noqa: E712
        )
        targets = [
            w
            for w in result.scalars().all()
            if event in (w.events or []) and (not w.index_ids or index.id in w.index_ids)
        ]
        if not targets:
            return 0

        payload = index_payload(index)
        for webhook in targets:
            await send_webhook(db, webhook, event, payload)
        await db.commit()
        return len(targets)
    except Exception:
        logger.exception("Webhook dispatch failed for index %s (%s)", index.id, event)
        await db.rollback()
        return 0
