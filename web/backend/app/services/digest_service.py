"""
Scheduled email reports.

Sends each email subscription its report when the schedule says one is due: a
summary of the subscriber's indices with trailing returns and top holdings, and
optionally a factsheet attached for each index.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.plans import FEATURE_DELIVERY, get_plan
from app.models.delivery import DeliveryLog, DeliveryStatus, DeliveryType, EmailSubscription
from app.models.index import Index
from app.models.user import User
from app.services import analytics_service, email_service
from app.services.analytics_service import AnalyticsUnavailableError
from app.services.schedule import is_due

logger = logging.getLogger(__name__)

# Bounds the size of one email and the work to build it.
MAX_INDICES_PER_REPORT = 15
MAX_ATTACHMENTS = 5
TOP_HOLDINGS = 5
RETURN_COLUMNS = ("1M", "3M", "YTD", "1Y")

PLAN_REQUIRED_MESSAGE = "Scheduled reports are part of the Pro plan."
NOT_CONFIGURED_MESSAGE = "Email sending is not set up on the server."
NO_INDICES_MESSAGE = "There are no indices with constituents to report on."


class DigestError(Exception):
    """A report could not be produced, for a reason worth showing the owner."""


def _pct(value: float | None) -> str:
    if value is None:
        return '<span style="color:#9ca3af">n/a</span>'
    colour = "#15803d" if value >= 0 else "#b91c1c"
    return f'<span style="color:{colour}">{value * 100:+.1f}%</span>'


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:60] or "index"


async def _load_indices(db: AsyncSession, subscription: EmailSubscription) -> list[Index]:
    query = (
        select(Index)
        .where(Index.owner_id == subscription.owner_id)
        .options(selectinload(Index.components))
        .order_by(Index.name)
    )
    if subscription.index_ids:
        query = query.where(Index.id.in_(subscription.index_ids))
    indices = (await db.execute(query)).scalars().all()
    reportable = [i for i in indices if any(c.is_active for c in i.components)]
    return reportable[:MAX_INDICES_PER_REPORT]


async def _trailing_returns(index: Index) -> dict[str, float | None]:
    try:
        analytics = await analytics_service.compute_index_analytics(index, "1Y")
    except AnalyticsUnavailableError:
        return {}
    except Exception:
        logger.exception("Analytics failed for index %s while building a report", index.id)
        return {}
    return analytics.get("trailing_returns") or {}


def _index_section(index: Index, returns: dict[str, float | None], with_holdings: bool) -> str:
    level = f"{index.current_value:,.2f}" if index.current_value else "n/a"
    url = f"{settings.FRONTEND_URL}/indices/{index.id}"
    cells = "".join(
        f'<td style="padding:8px 12px 8px 0"><div style="font-size:11px;color:#6b7280">{label}'
        f'</div><div style="font-size:15px;font-weight:600">{_pct(returns.get(label))}</div></td>'
        for label in RETURN_COLUMNS
    )
    section = (
        '<div style="border-top:1px solid #e5e7eb;padding:16px 0">'
        f'<a href="{html.escape(url, quote=True)}" style="font-size:16px;font-weight:700;'
        f'color:#111827;text-decoration:none">{html.escape(index.name)}</a>'
        f'<div style="font-size:13px;color:#6b7280">{html.escape(index.identifier)} · '
        f"Level {level}</div>"
        f'<table style="border-collapse:collapse;margin-top:8px"><tr>{cells}</tr></table>'
    )
    if with_holdings:
        top = sorted((c for c in index.components if c.is_active), key=lambda c: -(c.weight or 0))
        holdings = ", ".join(
            f"{html.escape(c.ticker)} {(c.weight or 0) * 100:.1f}%" for c in top[:TOP_HOLDINGS]
        )
        if holdings:
            section += f'<div style="font-size:13px;color:#374151">Top holdings: {holdings}</div>'
    return section + "</div>"


async def _factsheet_attachments(indices: list[Index]) -> list[email_service.Attachment]:
    # Imported here: the factsheet renderer lives with the reports endpoints.
    from app.api.v1.endpoints.reports import (
        calculate_performance_metrics,
        generate_factsheet_html,
    )

    attachments: list[email_service.Attachment] = []
    for index in indices[:MAX_ATTACHMENTS]:
        try:
            metrics = await calculate_performance_metrics(index)
            content = generate_factsheet_html(index, metrics)
        except Exception:
            logger.exception("Could not build a factsheet attachment for index %s", index.id)
            continue
        name = f"{_safe_filename(index.identifier or index.name)}_factsheet.html"
        attachments.append((name, content.encode(), "html"))
    return attachments


async def build_report(
    db: AsyncSession, subscription: EmailSubscription
) -> tuple[str, str, str, list[email_service.Attachment]]:
    """Subject, HTML body, text body and attachments for one subscription."""
    indices = await _load_indices(db, subscription)
    if not indices:
        raise DigestError(NO_INDICES_MESSAGE)

    with_holdings = subscription.report_type != "performance"
    sections, text_lines = [], []
    for index in indices:
        returns = await _trailing_returns(index)
        sections.append(_index_section(index, returns, with_holdings))
        one_month = returns.get("1M")
        text_lines.append(
            f"{index.name}: level {index.current_value or 'n/a'}"
            + (f", 1M {one_month * 100:+.1f}%" if one_month is not None else "")
        )

    today = datetime.now(timezone.utc).strftime("%-d %B %Y")
    title = f"{subscription.name}: {today}"
    manage = f"{settings.FRONTEND_URL}/settings/delivery"
    body = (
        '<p style="font-size:14px;color:#374151">Returns are for the current constituents '
        "over each period.</p>"
        f"{''.join(sections)}"
        f"{email_service.button('Open IndexMaker', settings.FRONTEND_URL + '/dashboard')}"
    )
    footer = (
        "You receive this because a scheduled report was set up in IndexMaker. "
        f'<a href="{html.escape(manage)}" style="color:#6b7280">Manage reports</a>'
    )
    attachments = await _factsheet_attachments(indices) if subscription.include_attachments else []
    text = "\n".join(text_lines) + f"\n\nManage reports: {manage}"
    return title, email_service.layout(title, body, footer), text, attachments


def _send_to_all(
    recipients: list[str],
    subject: str,
    html_body: str,
    text_body: str,
    attachments: list[email_service.Attachment],
) -> list[str]:
    """Send to each recipient; returns the addresses that failed. Blocking."""
    return [
        to
        for to in recipients
        if not email_service.send_email(to, subject, html_body, text_body, attachments=attachments)
    ]


async def send_subscription(db: AsyncSession, subscription: EmailSubscription) -> dict[str, Any]:
    """
    Build and send one subscription's report now, and record the outcome.

    `last_sent_at` only advances when at least one recipient got the email, so a
    total failure is retried on the next tick instead of being skipped until the
    next scheduled slot.
    """
    started = datetime.now(timezone.utc)
    sent_to: list[str] = []
    error: str | None = None

    owner = await db.get(User, subscription.owner_id)
    if owner is None or not get_plan(owner.tier).has(FEATURE_DELIVERY):
        error = PLAN_REQUIRED_MESSAGE
    elif not email_service.is_configured():
        error = NOT_CONFIGURED_MESSAGE
    else:
        try:
            subject, html_body, text_body, attachments = await build_report(db, subscription)
            recipients = list(subscription.recipients or [])
            failed = await asyncio.to_thread(
                _send_to_all, recipients, subject, html_body, text_body, attachments
            )
            sent_to = [r for r in recipients if r not in failed]
            if failed:
                error = f"Could not send to: {', '.join(failed)}"
        except DigestError as e:
            error = str(e)
        except Exception:
            logger.exception("Scheduled report %s failed", subscription.id)
            error = "The report could not be generated."

    finished = datetime.now(timezone.utc)
    if sent_to:
        subscription.last_sent_at = finished
    subscription.last_error = error
    db.add(
        DeliveryLog(
            delivery_type=DeliveryType.EMAIL.value,
            destination_id=subscription.id,
            status=(DeliveryStatus.SUCCESS if sent_to else DeliveryStatus.FAILED).value,
            payload_summary=f"{subscription.name}: sent to {len(sent_to)} recipient(s)",
            error_message=error,
            completed_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
        )
    )
    await db.commit()
    return {"sent": len(sent_to), "error": error}


async def send_due_subscriptions(db: AsyncSession, now: datetime) -> dict[str, int]:
    """Send every active subscription whose schedule has come due."""
    # Nothing can go out without SMTP, and writing a failure for every
    # subscription on every tick would only bury real errors in the log.
    if not email_service.is_configured():
        return {"due": 0, "sent": 0, "failed": 0}

    result = await db.execute(
        select(EmailSubscription)
        .join(User, User.id == EmailSubscription.owner_id)
        .where(EmailSubscription.is_active == True)  # noqa: E712
    )
    due = [
        s
        for s in result.scalars().all()
        if is_due(s.frequency, s.schedule_time, s.schedule_day, s.last_sent_at, s.created_at, now)
    ]

    sent = failed = 0
    for subscription in due:
        owner = await db.get(User, subscription.owner_id)
        # A lapsed plan pauses reports quietly; it is not an error to log hourly.
        if owner is None or not get_plan(owner.tier).has(FEATURE_DELIVERY):
            continue
        outcome = await send_subscription(db, subscription)
        if outcome["sent"]:
            sent += 1
        else:
            failed += 1

    if due:
        logger.info("Scheduled reports: %d due, %d sent, %d failed", len(due), sent, failed)
    return {"due": len(due), "sent": sent, "failed": failed}
