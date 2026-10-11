"""
Billing tests. Stripe is replaced with in-memory fakes: these verify what the
application does with Stripe's answers, not Stripe itself.
"""

from types import SimpleNamespace
from typing import Any

import pytest
import stripe
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import payments
from app.core.config import settings
from app.models.user import User

MONTHLY = {
    "id": "price_month",
    "active": True,
    "unit_amount": 1900,
    "currency": "usd",
    "recurring": {"interval": "month"},
}
ANNUAL = {
    "id": "price_year",
    "active": True,
    "unit_amount": 19000,
    "currency": "usd",
    "recurring": {"interval": "year"},
}


def subscription(
    sub_id: str = "sub_1",
    status: str = "active",
    interval: str = "month",
    user_id: str | None = None,
    customer: str = "cus_1",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": sub_id,
        "status": status,
        "customer": customer,
        "cancel_at_period_end": False,
        "metadata": {"user_id": user_id} if user_id else {},
        "items": {
            "data": [
                {
                    "current_period_end": 1_900_000_000,
                    "price": {"id": f"price_{interval}", "recurring": {"interval": interval}},
                }
            ]
        },
        **extra,
    }


@pytest.fixture
def billing(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Configure billing and capture every outbound Stripe call."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(settings, "STRIPE_PRO_MONTHLY_PRICE_ID", "price_month")
    monkeypatch.setattr(settings, "STRIPE_PRO_ANNUAL_PRICE_ID", "price_year")
    monkeypatch.setattr(settings, "STRIPE_PRO_PRICE_ID", None)
    monkeypatch.setattr(settings, "STRIPE_TRIAL_DAYS", 0)
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.test")
    payments._price_cache.update(at=0.0, prices={})

    state = SimpleNamespace(checkout_kwargs=None, portal_kwargs=None, subscriptions={}, event=None)

    monkeypatch.setattr(
        stripe.Price, "retrieve", lambda pid: {"price_month": MONTHLY, "price_year": ANNUAL}[pid]
    )
    monkeypatch.setattr(stripe.Customer, "list", lambda **kw: SimpleNamespace(data=[]))
    monkeypatch.setattr(stripe.Customer, "create", lambda **kw: SimpleNamespace(id="cus_new"))

    def create_checkout(**kwargs: Any) -> SimpleNamespace:
        state.checkout_kwargs = kwargs
        return SimpleNamespace(url="https://checkout.stripe.test/session")

    def create_portal(**kwargs: Any) -> SimpleNamespace:
        state.portal_kwargs = kwargs
        return SimpleNamespace(url="https://billing.stripe.test/portal")

    monkeypatch.setattr(stripe.checkout.Session, "create", create_checkout)
    monkeypatch.setattr(stripe.billing_portal.Session, "create", create_portal)
    monkeypatch.setattr(stripe.Subscription, "retrieve", lambda sid: state.subscriptions[sid])
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: state.event)
    yield state
    payments._price_cache.update(at=0.0, prices={})


async def send_event(client: AsyncClient, state: SimpleNamespace, type_: str, obj: dict) -> None:
    state.event = {"type": type_, "data": {"object": obj}}
    response = await client.post(
        "/api/v1/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert response.status_code == 200


class TestPlans:
    async def test_plans_are_public_and_priced_from_stripe(self, client: AsyncClient, billing):
        response = await client.get("/api/v1/payments/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["billing_enabled"] is True
        pro = next(p for p in data["plans"] if p["id"] == "pro")
        assert [(p["interval"], p["unit_amount"]) for p in pro["prices"]] == [
            ("month", 1900),
            ("year", 19000),
        ]
        assert next(p for p in data["plans"] if p["id"] == "free")["prices"] == []

    async def test_plans_without_stripe_still_lists_the_catalogue(
        self, client: AsyncClient, monkeypatch
    ):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
        payments._price_cache.update(at=0.0, prices={})
        data = (await client.get("/api/v1/payments/plans")).json()
        assert data["billing_enabled"] is False
        assert {p["id"] for p in data["plans"]} == {"free", "pro", "enterprise"}


class TestCheckout:
    async def test_checkout_uses_the_requested_interval(
        self, client: AsyncClient, auth_headers, billing, test_user: User
    ):
        response = await client.post(
            "/api/v1/payments/create-checkout-session",
            headers=auth_headers,
            json={"interval": "month"},
        )
        assert response.status_code == 200
        assert response.json()["checkoutUrl"].startswith("https://checkout.stripe.test")
        kwargs = billing.checkout_kwargs
        assert kwargs["line_items"] == [{"price": "price_month", "quantity": 1}]
        assert kwargs["client_reference_id"] == test_user.id
        assert kwargs["success_url"].startswith("https://app.test/payment/success")
        assert "trial_period_days" not in kwargs["subscription_data"]
        assert test_user.stripe_customer_id == "cus_new"

    async def test_checkout_defaults_to_annual_without_a_body(
        self, client: AsyncClient, auth_headers, billing
    ):
        response = await client.post(
            "/api/v1/payments/create-checkout-session", headers=auth_headers
        )
        assert response.status_code == 200
        assert billing.checkout_kwargs["line_items"][0]["price"] == "price_year"

    async def test_trial_applies_only_to_a_first_subscription(
        self, client: AsyncClient, auth_headers, billing, monkeypatch
    ):
        monkeypatch.setattr(settings, "STRIPE_TRIAL_DAYS", 14)
        await client.post("/api/v1/payments/create-checkout-session", headers=auth_headers)
        assert billing.checkout_kwargs["subscription_data"]["trial_period_days"] == 14

    async def test_existing_subscriber_cannot_start_a_second_checkout(
        self, client: AsyncClient, auth_headers, billing, test_user: User, db_session: AsyncSession
    ):
        test_user.subscription_id = "sub_1"
        test_user.subscription_status = "active"
        await db_session.commit()
        response = await client.post(
            "/api/v1/payments/create-checkout-session", headers=auth_headers
        )
        assert response.status_code == 409
        assert billing.checkout_kwargs is None

    async def test_checkout_unconfigured_is_503(
        self, client: AsyncClient, auth_headers, monkeypatch
    ):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
        response = await client.post(
            "/api/v1/payments/create-checkout-session", headers=auth_headers
        )
        assert response.status_code == 503


class TestPortal:
    async def test_portal_requires_a_billing_account(
        self, client: AsyncClient, auth_headers, billing
    ):
        response = await client.post("/api/v1/payments/portal", headers=auth_headers)
        assert response.status_code == 400

    async def test_portal_returns_url_for_customer(
        self, client: AsyncClient, auth_headers, billing, test_user: User, db_session: AsyncSession
    ):
        test_user.stripe_customer_id = "cus_1"
        await db_session.commit()
        response = await client.post("/api/v1/payments/portal", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["url"].startswith("https://billing.stripe.test")
        assert billing.portal_kwargs == {
            "customer": "cus_1",
            "return_url": "https://app.test/settings",
        }


class TestWebhook:
    async def test_checkout_completed_upgrades_and_records_period(
        self, client: AsyncClient, billing, test_user: User
    ):
        billing.subscriptions["sub_1"] = subscription(interval="year")
        await send_event(
            client,
            billing,
            "checkout.session.completed",
            {"client_reference_id": test_user.id, "customer": "cus_1", "subscription": "sub_1"},
        )
        assert test_user.tier == "pro"
        assert test_user.subscription_id == "sub_1"
        assert test_user.subscription_interval == "year"
        assert test_user.stripe_customer_id == "cus_1"
        assert test_user.subscription_current_period_end is not None

    async def test_past_due_keeps_access_then_cancellation_removes_it(
        self, client: AsyncClient, billing, test_user: User
    ):
        await send_event(
            client, billing, "customer.subscription.created", subscription(user_id=test_user.id)
        )
        assert test_user.tier == "pro"

        await send_event(
            client,
            billing,
            "customer.subscription.updated",
            subscription(status="past_due", user_id=test_user.id),
        )
        assert test_user.tier == "pro"
        assert test_user.subscription_status == "past_due"

        await send_event(
            client,
            billing,
            "customer.subscription.deleted",
            subscription(status="canceled", user_id=test_user.id),
        )
        assert test_user.tier == "free"
        assert test_user.subscription_status == "canceled"

    async def test_cancel_at_period_end_is_recorded_without_downgrading(
        self, client: AsyncClient, billing, test_user: User
    ):
        await send_event(
            client,
            billing,
            "customer.subscription.updated",
            subscription(user_id=test_user.id, cancel_at_period_end=True),
        )
        assert test_user.tier == "pro"
        assert test_user.subscription_cancel_at_period_end is True

    async def test_user_is_found_by_customer_when_metadata_is_missing(
        self, client: AsyncClient, billing, test_user: User, db_session: AsyncSession
    ):
        test_user.stripe_customer_id = "cus_1"
        await db_session.commit()
        await send_event(client, billing, "customer.subscription.updated", subscription())
        assert test_user.tier == "pro"

    async def test_late_event_for_an_old_subscription_does_not_downgrade(
        self, client: AsyncClient, billing, test_user: User
    ):
        await send_event(
            client,
            billing,
            "customer.subscription.created",
            subscription(sub_id="sub_new", user_id=test_user.id),
        )
        await send_event(
            client,
            billing,
            "customer.subscription.deleted",
            subscription(sub_id="sub_old", status="canceled", user_id=test_user.id),
        )
        assert test_user.tier == "pro"
        assert test_user.subscription_id == "sub_new"

    async def test_enterprise_is_never_demoted_by_a_subscription_event(
        self, client: AsyncClient, billing, admin_user: User
    ):
        await send_event(
            client,
            billing,
            "customer.subscription.deleted",
            subscription(status="canceled", user_id=admin_user.id),
        )
        assert admin_user.tier == "enterprise"

    async def test_failed_invoice_syncs_status_from_stripe(
        self, client: AsyncClient, billing, test_user: User, db_session: AsyncSession
    ):
        test_user.stripe_customer_id = "cus_1"
        test_user.subscription_id = "sub_1"
        test_user.subscription_status = "active"
        test_user.tier = "pro"
        await db_session.commit()
        billing.subscriptions["sub_1"] = subscription(status="past_due")
        await send_event(
            client,
            billing,
            "invoice.payment_failed",
            {
                "customer": "cus_1",
                "parent": {"subscription_details": {"subscription": "sub_1"}},
            },
        )
        assert test_user.subscription_status == "past_due"

    async def test_bad_signature_is_rejected(self, client: AsyncClient, billing, monkeypatch):
        def reject(payload, sig, secret):
            raise stripe.SignatureVerificationError("bad", sig)

        monkeypatch.setattr(stripe.Webhook, "construct_event", reject)
        response = await client.post(
            "/api/v1/payments/webhook", content=b"{}", headers={"stripe-signature": "x"}
        )
        assert response.status_code == 400


class TestVerifySession:
    async def test_verify_applies_a_completed_session_immediately(
        self, client: AsyncClient, auth_headers, billing, test_user: User, monkeypatch
    ):
        monkeypatch.setattr(
            stripe.checkout.Session,
            "retrieve",
            lambda sid, expand=None: {
                "status": "complete",
                "client_reference_id": test_user.id,
                "customer": "cus_1",
                "subscription": subscription(),
            },
        )
        response = await client.post(
            "/api/v1/payments/verify-session", headers=auth_headers, json={"session_id": "cs_1"}
        )
        assert response.status_code == 200
        assert response.json()["tier"] == "pro"
        assert response.json()["interval"] == "month"

    async def test_verify_refuses_someone_elses_session(
        self, client: AsyncClient, auth_headers, billing, test_user: User, monkeypatch
    ):
        monkeypatch.setattr(
            stripe.checkout.Session,
            "retrieve",
            lambda sid, expand=None: {
                "status": "complete",
                "client_reference_id": "another-user",
                "subscription": subscription(),
            },
        )
        response = await client.post(
            "/api/v1/payments/verify-session", headers=auth_headers, json={"session_id": "cs_1"}
        )
        assert response.status_code == 404
        assert test_user.tier == "free"


class TestSubscriptionSummary:
    async def test_summary_reports_plan_and_usage(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/payments/subscription", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "free"
        assert data["plan"]["max_indices"] == 3
        assert data["usage"] == {
            "indices": 0,
            "data_sources": 0,
            "public_shares": 0,
            "embed_widgets": 0,
        }
