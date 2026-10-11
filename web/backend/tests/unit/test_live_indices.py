"""Followers of public indices, scheduled email reports and the daily refresh."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import DeliveryLog, EmailSubscription
from app.models.embed import IndexFollower, PublicShare
from app.models.index import Index, IndexComponent, IndexSnapshot, IndexStatus
from app.models.user import User
from app.services import digest_service, email_service, refresh_service
from app.services.market_data_service import MarketDataService


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Capture outbound email instead of sending it."""
    sent: list[dict[str, Any]] = []

    def fake_send(to_email, subject, html_body, text_body=None, **extra):
        sent.append({"to": to_email, "subject": subject, "html": html_body, **extra})
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)
    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    return sent


@pytest.fixture
async def pro_user(test_user: User, db_session: AsyncSession) -> User:
    test_user.tier = "pro"
    await db_session.commit()
    return test_user


async def make_index(db: AsyncSession, owner: User, identifier: str = "LIVE") -> Index:
    index = Index(
        owner_id=owner.id,
        name="Live Index",
        identifier=identifier,
        base_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        base_value=1000.0,
        divisor=1.0,
        current_value=1000.0,
        status=IndexStatus.ACTIVE.value,
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


async def make_share(db: AsyncSession, index: Index, **extra: Any) -> PublicShare:
    share = PublicShare(index_id=index.id, owner_id=index.owner_id, slug="live-index", **extra)
    db.add(share)
    await db.commit()
    return share


async def follower_for(db: AsyncSession, share: PublicShare) -> IndexFollower | None:
    result = await db.execute(select(IndexFollower).where(IndexFollower.share_id == share.id))
    return result.scalar_one_or_none()


FOLLOW = "/api/v1/embeds/public/shares/live-index/follow"


class TestFollowing:
    async def test_follow_sends_a_confirmation_and_nothing_else(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession, outbox
    ):
        share = await make_share(db_session, await make_index(db_session, test_user))

        response = await client.post(FOLLOW, json={"email": "Reader@Example.com"})

        assert response.status_code == 202
        follower = await follower_for(db_session, share)
        assert follower.email == "reader@example.com"
        assert follower.confirmed_at is None
        assert len(outbox) == 1
        assert follower.token in outbox[0]["html"]

    async def test_repeat_requests_do_not_send_more_mail(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession, outbox
    ):
        await make_share(db_session, await make_index(db_session, test_user))

        await client.post(FOLLOW, json={"email": "reader@example.com"})
        again = await client.post(FOLLOW, json={"email": "reader@example.com"})

        # Same answer either way, so the form does not reveal who follows.
        assert again.status_code == 202
        assert len(outbox) == 1

    async def test_confirming_counts_the_follower(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession, outbox
    ):
        share = await make_share(db_session, await make_index(db_session, test_user))
        await client.post(FOLLOW, json={"email": "reader@example.com"})
        follower = await follower_for(db_session, share)

        before = await client.get("/api/v1/embeds/public/shares/live-index")
        confirmed = await client.post(f"/api/v1/embeds/public/follow/confirm/{follower.token}")
        after = await client.get("/api/v1/embeds/public/shares/live-index")

        assert confirmed.status_code == 200
        assert confirmed.json() == {"title": "Live Index", "slug": "live-index"}
        assert before.json()["follower_count"] == 0
        assert after.json()["follower_count"] == 1

    async def test_unsubscribe_deletes_the_address(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession, outbox
    ):
        share = await make_share(db_session, await make_index(db_session, test_user))
        await client.post(FOLLOW, json={"email": "reader@example.com"})
        token = (await follower_for(db_session, share)).token

        first = await client.post(f"/api/v1/embeds/public/follow/unsubscribe/{token}")
        second = await client.post(f"/api/v1/embeds/public/follow/unsubscribe/{token}")

        assert first.status_code == 200
        assert second.status_code == 404
        assert await follower_for(db_session, share) is None

    async def test_protected_and_missing_shares_cannot_be_followed(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession, outbox
    ):
        await make_share(db_session, await make_index(db_session, test_user), password_hash="x")

        protected = await client.post(FOLLOW, json={"email": "reader@example.com"})
        missing = await client.post(
            "/api/v1/embeds/public/shares/nope/follow", json={"email": "reader@example.com"}
        )

        assert protected.status_code == 403
        assert missing.status_code == 404
        assert outbox == []


class TestRebalanceNotifications:
    async def _confirmed_follower(self, db: AsyncSession, share: PublicShare, email: str) -> None:
        db.add(
            IndexFollower(
                share_id=share.id,
                email=email,
                token=f"tok-{email}",
                confirmed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    async def test_confirmed_followers_are_emailed_on_rebalance(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, outbox
    ):
        index = await make_index(db_session, test_user)
        share = await make_share(db_session, index)
        await self._confirmed_follower(db_session, share, "reader@example.com")
        db_session.add(IndexFollower(share_id=share.id, email="unconfirmed@example.com", token="u"))
        await db_session.commit()

        response = await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)

        assert response.status_code == 200
        assert [m["to"] for m in outbox] == ["reader@example.com"]
        message = outbox[0]
        assert "rebalanced" in message["subject"]
        assert "AAA" in message["html"]
        assert message["unsubscribe_url"].endswith("/follow/unsubscribe/tok-reader@example.com")

    async def test_hidden_constituents_are_not_leaked_by_email(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, outbox
    ):
        index = await make_index(db_session, test_user)
        share = await make_share(db_session, index, show_components=False)
        await self._confirmed_follower(db_session, share, "reader@example.com")

        await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)

        assert len(outbox) == 1
        assert "AAA" not in outbox[0]["html"]

    async def test_a_switched_off_share_goes_quiet(
        self, client: AsyncClient, auth_headers, test_user: User, db_session: AsyncSession, outbox
    ):
        index = await make_index(db_session, test_user)
        share = await make_share(db_session, index, is_active=False)
        await self._confirmed_follower(db_session, share, "reader@example.com")

        await client.post(f"/api/v1/indices/{index.id}/rebalance", headers=auth_headers)

        assert outbox == []


async def make_subscription(db: AsyncSession, owner: User, **extra: Any) -> EmailSubscription:
    values: dict[str, Any] = {
        "name": "Weekly summary",
        "recipients": ["me@example.com", "boss@example.com"],
        "frequency": "daily",
        "schedule_time": "08:00",
        "include_attachments": False,
        "created_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
    }
    values.update(extra)
    subscription = EmailSubscription(owner_id=owner.id, **values)
    db.add(subscription)
    await db.commit()
    return subscription


NOW = datetime(2026, 10, 14, 8, 20, tzinfo=timezone.utc)


class TestScheduledReports:
    async def test_a_due_report_goes_to_every_recipient(
        self, pro_user: User, db_session: AsyncSession, outbox
    ):
        await make_index(db_session, pro_user)
        subscription = await make_subscription(db_session, pro_user)

        outcome = await digest_service.send_due_subscriptions(db_session, NOW)

        assert outcome == {"due": 1, "sent": 1, "failed": 0}
        assert [m["to"] for m in outbox] == ["me@example.com", "boss@example.com"]
        assert "Live Index" in outbox[0]["html"]
        assert subscription.last_sent_at is not None
        assert subscription.last_error is None
        logs = (await db_session.execute(select(DeliveryLog))).scalars().all()
        assert [log.status for log in logs] == ["success"]

    async def test_a_report_is_not_sent_twice_for_one_slot(
        self, pro_user: User, db_session: AsyncSession, outbox
    ):
        # The send is stamped with the real clock, so this one runs in real time.
        now = datetime.now(timezone.utc)
        await make_index(db_session, pro_user)
        await make_subscription(
            db_session, pro_user, schedule_time="00:00", created_at=now - timedelta(days=2)
        )

        await digest_service.send_due_subscriptions(db_session, now)
        again = await digest_service.send_due_subscriptions(db_session, now + timedelta(seconds=5))

        assert again["due"] == 0
        assert len(outbox) == 2

    async def test_free_plan_and_paused_reports_stay_quiet(
        self, test_user: User, db_session: AsyncSession, outbox
    ):
        await make_index(db_session, test_user)
        await make_subscription(db_session, test_user)
        await make_subscription(db_session, test_user, is_active=False)

        outcome = await digest_service.send_due_subscriptions(db_session, NOW)

        assert outcome["sent"] == 0
        assert outbox == []

    async def test_factsheets_are_attached_when_asked_for(
        self, pro_user: User, db_session: AsyncSession, outbox
    ):
        await make_index(db_session, pro_user)
        await make_subscription(db_session, pro_user, include_attachments=True)

        await digest_service.send_due_subscriptions(db_session, NOW)

        name, content, subtype = outbox[0]["attachments"][0]
        assert name == "LIVE_factsheet.html"
        assert subtype == "html"
        assert b"Live Index" in content

    async def test_total_failure_is_recorded_and_retried(
        self, pro_user: User, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(email_service, "is_configured", lambda: True)
        monkeypatch.setattr(email_service, "send_email", lambda *a, **k: False)
        await make_index(db_session, pro_user)
        subscription = await make_subscription(db_session, pro_user)

        first = await digest_service.send_due_subscriptions(db_session, NOW)
        second = await digest_service.send_due_subscriptions(db_session, NOW + timedelta(hours=1))

        assert first["failed"] == 1
        # Not marked as sent, so the next tick tries again.
        assert second["due"] == 1
        assert subscription.last_sent_at is None
        assert "Could not send" in subscription.last_error

    async def test_creating_a_report_needs_pro(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/delivery/email",
            headers=auth_headers,
            json={"name": "Weekly", "recipients": ["me@example.com"]},
        )

        assert response.status_code == 402
        assert response.json()["detail"]["code"] == "upgrade_required"

    async def test_send_now_reports_the_outcome(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession, outbox
    ):
        await make_index(db_session, pro_user)
        created = await client.post(
            "/api/v1/delivery/email",
            headers=auth_headers,
            json={"name": "Weekly", "recipients": ["me@example.com"], "frequency": "weekly"},
        )
        assert created.status_code == 201

        response = await client.post(
            f"/api/v1/delivery/email/{created.json()['id']}/send-now", headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["last_sent_at"] is not None
        assert [m["to"] for m in outbox] == ["me@example.com"]

    async def test_send_now_explains_why_nothing_went(
        self, client: AsyncClient, auth_headers, pro_user: User, db_session: AsyncSession, outbox
    ):
        subscription = await make_subscription(db_session, pro_user)

        response = await client.post(
            f"/api/v1/delivery/email/{subscription.id}/send-now", headers=auth_headers
        )

        assert response.status_code == 502
        assert response.json()["detail"] == digest_service.NO_INDICES_MESSAGE

    @pytest.mark.parametrize("frequency", ["hourly", "realtime", "sometimes"])
    async def test_only_scheduled_frequencies_are_accepted(
        self, client: AsyncClient, auth_headers, pro_user: User, frequency: str
    ):
        response = await client.post(
            "/api/v1/delivery/email",
            headers=auth_headers,
            json={"name": "x", "recipients": ["me@example.com"], "frequency": frequency},
        )
        assert response.status_code == 422


@pytest.fixture
def priced(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    """Quotes the refresh will see."""
    prices = {"AAA": 66.0, "BBB": 40.0}

    async def info(self: MarketDataService, ticker: str) -> dict[str, Any] | None:
        return {"price": prices[ticker], "name": ticker} if ticker in prices else None

    monkeypatch.setattr(MarketDataService, "get_security_info", info)
    return prices


# A Wednesday evening, after the close.
AFTER_CLOSE = datetime(2026, 10, 14, 22, 5, tzinfo=timezone.utc)


class TestDailyRefresh:
    async def _snapshots(self, db: AsyncSession, index_id: str) -> list[IndexSnapshot]:
        result = await db.execute(select(IndexSnapshot).where(IndexSnapshot.index_id == index_id))
        return list(result.scalars().all())

    async def test_a_paid_index_is_repriced_and_snapshotted(
        self, pro_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, pro_user)

        outcome = await refresh_service.refresh_stale_indices(db_session, AFTER_CLOSE)

        assert outcome == {"candidates": 1, "refreshed": 1, "failed": 0}
        await db_session.refresh(index)
        # AAA rose 10% at a 60% weight: the level moves 6%, with no jump.
        assert index.current_value == pytest.approx(1060.0)
        assert len(await self._snapshots(db_session, index.id)) == 1

    async def test_a_free_private_index_is_left_alone(
        self, test_user: User, db_session: AsyncSession, priced
    ):
        await make_index(db_session, test_user)

        outcome = await refresh_service.refresh_stale_indices(db_session, AFTER_CLOSE)

        assert outcome["candidates"] == 0

    async def test_a_publicly_shared_index_is_kept_current_on_any_plan(
        self, test_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, test_user)
        await make_share(db_session, index)

        outcome = await refresh_service.refresh_stale_indices(db_session, AFTER_CLOSE)

        assert outcome["refreshed"] == 1

    async def test_an_index_already_calculated_since_the_close_is_skipped(
        self, pro_user: User, db_session: AsyncSession, priced
    ):
        index = await make_index(db_session, pro_user)
        index.last_calculated = AFTER_CLOSE - timedelta(minutes=10)
        await db_session.commit()

        outcome = await refresh_service.refresh_stale_indices(db_session, AFTER_CLOSE)

        assert outcome["candidates"] == 0

    async def test_one_failing_index_does_not_stop_the_rest(
        self, pro_user: User, db_session: AsyncSession, priced, monkeypatch: pytest.MonkeyPatch
    ):
        # Ids are read up front: the rollback after the failure expires the objects.
        good_id = (await make_index(db_session, pro_user, "GOOD")).id
        bad_id = (await make_index(db_session, pro_user, "BAD")).id
        original = refresh_service.IndexService.calculate_index

        async def flaky(self, index: Index) -> None:
            if index.id == bad_id:
                raise RuntimeError("quote service down")
            await original(self, index)

        monkeypatch.setattr(refresh_service.IndexService, "calculate_index", flaky)

        outcome = await refresh_service.refresh_stale_indices(db_session, AFTER_CLOSE)

        assert outcome == {"candidates": 2, "refreshed": 1, "failed": 1}
        assert len(await self._snapshots(db_session, good_id)) == 1
