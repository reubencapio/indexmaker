"""
Followers of publicly shared indices.

A visitor to a public index page can leave an email address to be told when the
index is rebalanced. The address is confirmed from the inbox before it is ever
used (so nobody can sign a stranger up), and every message carries a one-click
link that removes it.
"""

from __future__ import annotations

import asyncio
import html
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.embed import IndexFollower, PublicShare
from app.models.index import Index
from app.services import email_service

logger = logging.getLogger(__name__)

# A second request for the same address inside this window is ignored, so the
# form cannot be used to flood someone's inbox with confirmation emails.
CONFIRMATION_RESEND_AFTER = timedelta(minutes=10)

MAX_HOLDINGS_IN_EMAIL = 10


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    html_body: str
    text_body: str
    unsubscribe_url: str | None = None


def share_title(share: PublicShare, index: Index) -> str:
    return share.title_override or index.name


def confirm_url(token: str) -> str:
    return f"{settings.FRONTEND_URL}/follow/confirm/{token}"


def unsubscribe_url(token: str) -> str:
    return f"{settings.FRONTEND_URL}/follow/unsubscribe/{token}"


def send_all(messages: list[OutgoingEmail]) -> int:
    """Send each message; returns how many were accepted. Blocking."""
    sent = 0
    for message in messages:
        if email_service.send_email(
            message.to,
            message.subject,
            message.html_body,
            message.text_body,
            unsubscribe_url=message.unsubscribe_url,
        ):
            sent += 1
    return sent


def _confirmation_email(follower: IndexFollower, title: str) -> OutgoingEmail:
    url = confirm_url(follower.token)
    body = (
        f"<p>Confirm your email address to follow <strong>{html.escape(title)}</strong>. "
        "You will be emailed when it is rebalanced.</p>"
        f"{email_service.button('Confirm and follow', url)}"
        '<p style="color:#6b7280;font-size:13px">If you did not ask for this, ignore this '
        "email and you will not hear from us again.</p>"
    )
    return OutgoingEmail(
        to=follower.email,
        subject=f"Confirm you want to follow {title}",
        html_body=email_service.layout(f"Follow {title}", body),
        text_body=(
            f"Confirm your email address to follow {title}:\n{url}\n\n"
            "If you did not ask for this, ignore this email."
        ),
    )


async def request_follow(db: AsyncSession, share: PublicShare, index: Index, email: str) -> None:
    """
    Record a follow request and email a confirmation link.

    Silent about whether the address was already following: the response to a
    public form must not reveal who is on the list.
    """
    email = email.strip().lower()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(IndexFollower).where(
            IndexFollower.share_id == share.id, IndexFollower.email == email
        )
    )
    follower = result.scalar_one_or_none()

    if follower and follower.confirmed_at:
        return
    if follower and follower.confirmation_sent_at:
        if now - follower.confirmation_sent_at < CONFIRMATION_RESEND_AFTER:
            return
    if follower is None:
        follower = IndexFollower(share_id=share.id, email=email, token=secrets.token_urlsafe(32))
        db.add(follower)

    follower.confirmation_sent_at = now
    await db.commit()

    message = _confirmation_email(follower, share_title(share, index))
    await asyncio.to_thread(send_all, [message])


async def _follower_and_share(
    db: AsyncSession, token: str
) -> tuple[IndexFollower, PublicShare, Index] | None:
    result = await db.execute(
        select(IndexFollower, PublicShare, Index)
        .join(PublicShare, PublicShare.id == IndexFollower.share_id)
        .join(Index, Index.id == PublicShare.index_id)
        .where(IndexFollower.token == token)
    )
    row = result.first()
    return (row[0], row[1], row[2]) if row else None


async def confirm(db: AsyncSession, token: str) -> tuple[PublicShare, Index] | None:
    """Confirm a follower. Idempotent, so reopening the link is harmless."""
    found = await _follower_and_share(db, token)
    if not found:
        return None
    follower, share, index = found
    if not follower.confirmed_at:
        follower.confirmed_at = datetime.now(timezone.utc)
        await db.commit()
    return share, index


async def unsubscribe(db: AsyncSession, token: str) -> tuple[PublicShare, Index] | None:
    """Remove a follower. The address is deleted, not merely flagged."""
    found = await _follower_and_share(db, token)
    if not found:
        return None
    follower, share, index = found
    await db.delete(follower)
    await db.commit()
    return share, index


def _holdings_table(index: Index, previous_weights: dict[str, float]) -> str:
    active = sorted((c for c in index.components if c.is_active), key=lambda c: -(c.weight or 0))
    rows = []
    for c in active[:MAX_HOLDINGS_IN_EMAIL]:
        weight = c.weight or 0
        before = previous_weights.get(c.ticker)
        if before is None:
            change = "new"
        else:
            change = f"{(weight - before) * 100:+.1f} pts"
        rows.append(
            "<tr>"
            f'<td style="padding:6px 0;font-weight:600">{html.escape(c.ticker)}</td>'
            f'<td style="padding:6px 8px;color:#6b7280">{html.escape(c.name or "")}</td>'
            f'<td style="padding:6px 0;text-align:right">{weight * 100:.1f}%</td>'
            f'<td style="padding:6px 0 6px 12px;text-align:right;color:#6b7280">{change}</td>'
            "</tr>"
        )
    more = len(active) - MAX_HOLDINGS_IN_EMAIL
    note = f'<p style="color:#6b7280;font-size:13px">and {more} more.</p>' if more > 0 else ""
    return (
        '<table style="width:100%;border-collapse:collapse;font-size:14px;margin:8px 0">'
        '<tr style="color:#6b7280;font-size:12px;text-align:left">'
        '<th style="padding:4px 0">Ticker</th><th style="padding:4px 8px">Name</th>'
        '<th style="padding:4px 0;text-align:right">Weight</th>'
        '<th style="padding:4px 0 4px 12px;text-align:right">Change</th></tr>'
        f"{''.join(rows)}</table>{note}"
    )


async def rebalance_notifications(
    db: AsyncSession, index: Index, previous_weights: dict[str, float]
) -> list[OutgoingEmail]:
    """
    Build the emails telling an index's followers it was rebalanced.

    Returned, not sent, so the caller can hand the slow part (SMTP) to a
    background task after the database work is finished.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(IndexFollower, PublicShare)
        .join(PublicShare, PublicShare.id == IndexFollower.share_id)
        .where(PublicShare.index_id == index.id)
        .where(PublicShare.is_active == True)  # noqa: E712
        .where(IndexFollower.confirmed_at.is_not(None))
    )

    messages: list[OutgoingEmail] = []
    for follower, share in result.all():
        if share.expires_at and share.expires_at < now:
            continue
        title = share_title(share, index)
        stop = unsubscribe_url(follower.token)
        level = f"{index.current_value:,.2f}" if index.current_value else "n/a"

        body = f"<p><strong>{html.escape(title)}</strong> has been rebalanced.</p>"
        body += f'<p style="font-size:14px">Index level: <strong>{level}</strong></p>'
        # A share that hides its constituents on the page must not leak them by email.
        if share.show_components:
            body += _holdings_table(index, previous_weights)
        body += email_service.button("View the index", share.public_url)

        messages.append(
            OutgoingEmail(
                to=follower.email,
                subject=f"{title} was rebalanced",
                html_body=email_service.layout(
                    f"{title} was rebalanced",
                    body,
                    f'You follow this index on IndexMaker. <a href="{html.escape(stop)}" '
                    'style="color:#6b7280">Unsubscribe</a>',
                ),
                text_body=(
                    f"{title} has been rebalanced. Index level: {level}\n"
                    f"View it: {share.public_url}\n\nUnsubscribe: {stop}"
                ),
                unsubscribe_url=stop,
            )
        )
    return messages
