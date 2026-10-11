"""
Billing endpoints: plan catalogue, Stripe Checkout, the customer portal and the
webhook that keeps a user's tier in step with their subscription.
"""

import asyncio
import logging
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal

import stripe
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentActiveUser, DBSession
from app.core.config import settings
from app.core.plans import ENTERPRISE, FREE, PLANS, PRO, get_plan
from app.models.data_source import CustomDataSource
from app.models.embed import EmbedWidget, PublicShare
from app.models.index import Index
from app.models.user import User, UserTier

logger = logging.getLogger(__name__)

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

# Statuses that keep paid access. `past_due` is included deliberately: Stripe
# retries a failed renewal for days before giving up, and locking a customer out
# on the first declined card turns a recoverable payment into a cancellation.
# Access ends when Stripe finally moves the subscription to canceled or unpaid.
ENTITLED_STATUSES = {"active", "trialing", "past_due"}

# Statuses that mean "this user already has a subscription to manage", so a new
# checkout would double-bill them.
LIVE_STATUSES = ENTITLED_STATUSES | {"incomplete", "unpaid", "paused"}

PRICE_CACHE_SECONDS = 600
_price_cache: dict[str, Any] = {"at": 0.0, "prices": {}}

Interval = Literal["month", "year"]


class CheckoutRequest(BaseModel):
    interval: Interval = "year"


class VerifySessionRequest(BaseModel):
    session_id: str


# The Stripe SDK is synchronous, so every call is pushed to a worker thread;
# calling it inline would block the event loop for the whole round-trip.
async def _stripe_call(func_: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking Stripe SDK call without stalling the event loop."""
    return await asyncio.to_thread(lambda: func_(*args, **kwargs))


def _billing_enabled() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and _configured_price_ids())


def _configured_price_ids() -> list[str]:
    """Configured Pro price ids, de-duplicated, in a stable order."""
    ids = [
        settings.STRIPE_PRO_MONTHLY_PRICE_ID,
        settings.STRIPE_PRO_ANNUAL_PRICE_ID,
        # Pre-dates the monthly/annual split; still honoured so an existing
        # deployment keeps working without a config change.
        settings.STRIPE_PRO_PRICE_ID,
    ]
    return list(dict.fromkeys(i for i in ids if i))


async def _load_prices() -> dict[str, dict[str, Any]]:
    """
    Pro prices keyed by billing interval, read from Stripe.

    The interval and amount come from the Price object rather than from the name
    of the environment variable it was configured under. The pricing page shows
    exactly what Checkout will charge, even if an id was pasted into the wrong
    variable or the amount is later changed in the Stripe dashboard.
    """
    if not settings.STRIPE_SECRET_KEY:
        return {}

    now = time.monotonic()
    if _price_cache["prices"] and now - _price_cache["at"] < PRICE_CACHE_SECONDS:
        return _price_cache["prices"]

    prices: dict[str, dict[str, Any]] = {}
    for price_id in _configured_price_ids():
        try:
            price = await _stripe_call(stripe.Price.retrieve, price_id)
        except stripe.StripeError:
            logger.exception("Could not load Stripe price %s", price_id)
            continue

        recurring = price.get("recurring") or {}
        interval = recurring.get("interval")
        if (
            not price.get("active")
            or interval not in ("month", "year")
            or price.get("unit_amount") is None
        ):
            logger.warning("Stripe price %s is not an active monthly/yearly price", price_id)
            continue

        # First configured price wins for an interval.
        prices.setdefault(
            interval,
            {
                "id": price["id"],
                "interval": interval,
                "unit_amount": price["unit_amount"],
                "currency": price["currency"],
            },
        )

    if prices:
        _price_cache.update(at=now, prices=prices)
    return prices


def _timestamp(value: Any) -> datetime | None:
    return datetime.fromtimestamp(value, tz=timezone.utc) if value else None


def _first_item(subscription: Mapping[str, Any]) -> Mapping[str, Any]:
    items = (subscription.get("items") or {}).get("data") or []
    return items[0] if items else {}


def _apply_subscription_state(user: User, subscription: Mapping[str, Any]) -> None:
    """Sync a user's tier and subscription fields from a Stripe subscription."""
    item = _first_item(subscription)
    sub_status = subscription["status"]

    user.subscription_id = subscription["id"]
    user.subscription_status = sub_status
    user.subscription_interval = ((item.get("price") or {}).get("recurring") or {}).get("interval")
    # Newer Stripe API versions report the period on the subscription item;
    # older ones on the subscription itself.
    user.subscription_current_period_end = _timestamp(
        item.get("current_period_end") or subscription.get("current_period_end")
    )
    user.subscription_cancel_at_period_end = bool(
        subscription.get("cancel_at_period_end") or subscription.get("cancel_at")
    )

    # Enterprise is granted by hand, outside Stripe. A self-serve subscription
    # event must never demote it.
    if user.tier == ENTERPRISE:
        return
    user.tier = UserTier.PRO.value if sub_status in ENTITLED_STATUSES else UserTier.FREE.value


def _is_stale_event(user: User, subscription: Mapping[str, Any]) -> bool:
    """
    True when an event is about a subscription other than the user's live one.

    Stripe does not guarantee delivery order. Without this, a late "deleted" event
    for a long-replaced subscription would downgrade a customer who is paying on a
    newer one.
    """
    if not user.subscription_id or user.subscription_id == subscription["id"]:
        return False
    return (
        user.subscription_status in ENTITLED_STATUSES
        and subscription["status"] not in ENTITLED_STATUSES
    )


async def _find_user(db: DBSession, obj: Mapping[str, Any], subscription_id: str | None) -> Any:
    """Resolve the user an event belongs to: metadata, then subscription, then customer."""
    user_id = (obj.get("metadata") or {}).get("user_id") or obj.get("client_reference_id")
    if user_id:
        user = await db.get(User, user_id)
        if user:
            return user

    if subscription_id:
        result = await db.execute(select(User).where(User.subscription_id == subscription_id))
        user = result.scalar_one_or_none()
        if user:
            return user

    customer_id = obj.get("customer")
    if customer_id:
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        return result.scalars().first()
    return None


async def _count(db: DBSession, model: Any, user: User) -> int:
    return await db.scalar(select(func.count(model.id)).where(model.owner_id == user.id)) or 0


async def _subscription_payload(db: DBSession, user: User) -> dict[str, Any]:
    plan = get_plan(user.tier)
    return {
        "tier": plan.id,
        "plan": plan.to_public_dict(),
        "status": user.subscription_status,
        "interval": user.subscription_interval,
        "current_period_end": user.subscription_current_period_end,
        "cancel_at_period_end": user.subscription_cancel_at_period_end,
        "has_billing_account": bool(user.stripe_customer_id),
        "billing_enabled": _billing_enabled(),
        "usage": {
            "indices": await _count(db, Index, user),
            "data_sources": await _count(db, CustomDataSource, user),
            "public_shares": await _count(db, PublicShare, user),
            "embed_widgets": await _count(db, EmbedWidget, user),
        },
    }


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    """
    Public plan catalogue with live prices.

    Unauthenticated on purpose: the landing page renders pricing from it.
    """
    prices = await _load_prices()
    plans = []
    for plan_id in (FREE, PRO, ENTERPRISE):
        entry = PLANS[plan_id].to_public_dict()
        entry["prices"] = (
            [prices[i] for i in ("month", "year") if i in prices] if plan_id == PRO else []
        )
        plans.append(entry)

    return {
        "plans": plans,
        "billing_enabled": bool(prices),
        "trial_days": settings.STRIPE_TRIAL_DAYS,
    }


@router.get("/subscription")
async def get_subscription(user: CurrentActiveUser, db: DBSession) -> dict[str, Any]:
    """The caller's plan, subscription state and usage against plan limits."""
    return await _subscription_payload(db, user)


@router.post("/create-checkout-session")
async def create_checkout_session(
    user: CurrentActiveUser,
    db: DBSession,
    body: CheckoutRequest | None = None,
) -> dict:
    """Create a Stripe Checkout Session for a Pro subscription."""
    interval = body.interval if body else "year"

    if not _billing_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment configuration missing",
        )

    if user.subscription_id and user.subscription_status in LIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a subscription. Manage it from billing settings.",
        )

    try:
        prices = await _load_prices()
        # Fall back to whichever interval is configured: a deployment with a single
        # price should still be able to sell it.
        price = prices.get(interval) or next(iter(prices.values()), None)
        if price is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment configuration missing",
            )

        # Check if user already has a Stripe customer ID
        customer_id = user.stripe_customer_id

        # If not, try to find existing customer by email or create new one
        if not customer_id:
            customers = await _stripe_call(stripe.Customer.list, email=user.email, limit=1)
            if customers.data:
                customer_id = customers.data[0].id
            else:
                customer = await _stripe_call(
                    stripe.Customer.create,
                    email=user.email,
                    name=user.full_name,
                    metadata={"user_id": str(user.id)},
                )
                customer_id = customer.id

            # Persist the customer id now. Waiting for the webhook to do it means
            # every checkout attempt before the first successful payment creates
            # (or re-looks-up) a customer, and abandoned checkouts leave the user
            # permanently unlinked.
            user.stripe_customer_id = customer_id
            await db.commit()

        subscription_data: dict[str, Any] = {"metadata": {"user_id": str(user.id)}}
        # A trial is a first-subscription offer: anyone who has subscribed before
        # is excluded, or cancel-and-resubscribe would be an endless free plan.
        if settings.STRIPE_TRIAL_DAYS > 0 and not user.subscription_id:
            subscription_data["trial_period_days"] = settings.STRIPE_TRIAL_DAYS

        # No payment_method_types: Checkout then offers every method enabled in
        # the Stripe dashboard (wallets included) instead of cards only.
        checkout_session = await _stripe_call(
            stripe.checkout.Session.create,
            customer=customer_id,
            client_reference_id=str(user.id),
            line_items=[{"price": price["id"], "quantity": 1}],
            mode="subscription",
            allow_promotion_codes=True,
            billing_address_collection="auto",
            success_url=f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/payment/cancel",
            subscription_data=subscription_data,
        )
        return {"checkoutUrl": checkout_session.url}
    except stripe.StripeError:
        # Stripe error text can carry account/internal detail, so it is logged
        # rather than returned to the caller.
        logger.exception("Stripe checkout session creation failed for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not start checkout. Please try again.",
        )


@router.post("/portal")
async def create_portal_session(user: CurrentActiveUser) -> dict:
    """
    Open the Stripe customer portal: update card, switch plan, download
    invoices, cancel.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment configuration missing",
        )
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account yet. Subscribe to a plan first.",
        )

    try:
        session = await _stripe_call(
            stripe.billing_portal.Session.create,
            customer=user.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/settings",
        )
        return {"url": session.url}
    except stripe.StripeError:
        logger.exception("Stripe portal session creation failed for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not open billing portal. Please try again.",
        )


@router.post("/verify-session")
async def verify_checkout_session(
    body: VerifySessionRequest,
    user: CurrentActiveUser,
    db: DBSession,
) -> dict[str, Any]:
    """
    Confirm a finished checkout and apply it immediately.

    The webhook is the source of truth, but it can land seconds after the browser
    is redirected back. Reading the session here means the customer sees their
    upgrade the moment they return, rather than a "Free plan" page they just
    paid to leave.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment configuration missing",
        )

    try:
        session = await _stripe_call(
            stripe.checkout.Session.retrieve, body.session_id, expand=["subscription"]
        )
    except stripe.StripeError:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    # A session id is not a secret. Only its owner may redeem it.
    if session.get("client_reference_id") != str(user.id):
        raise HTTPException(status_code=404, detail="Checkout session not found")

    subscription = session.get("subscription")
    if session.get("status") == "complete" and isinstance(subscription, Mapping):
        if session.get("customer"):
            user.stripe_customer_id = session["customer"]
        if not _is_stale_event(user, subscription):
            _apply_subscription_state(user, subscription)
        await db.commit()

    return await _subscription_payload(db, user)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: DBSession,
    stripe_signature: str = Header(None),
):
    """
    Stripe webhook handler.

    Every branch re-reads state from the event (or from Stripe) and writes it
    idempotently, so a redelivered event is harmless.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured",
        )

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        # `obj` is a Checkout Session: the subscription id is a field on it.
        subscription_id = obj.get("subscription")
        user = await _find_user(db, obj, subscription_id)
        if user:
            if obj.get("customer"):
                user.stripe_customer_id = obj["customer"]

            if subscription_id:
                # Trust the subscription's own status rather than assuming active.
                subscription = await _stripe_call(stripe.Subscription.retrieve, subscription_id)
                if not _is_stale_event(user, subscription):
                    _apply_subscription_state(user, subscription)

            await db.commit()

    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        # `obj` IS the subscription here -- its id and status live at the top
        # level, not under a "subscription" key. A deleted subscription arrives
        # with status "canceled", so it needs no special handling.
        user = await _find_user(db, obj, obj["id"])
        if user and not _is_stale_event(user, obj):
            if obj.get("customer"):
                user.stripe_customer_id = obj["customer"]
            _apply_subscription_state(user, obj)
            await db.commit()

    elif event_type in ("invoice.payment_failed", "invoice.paid"):
        # The invoice does not carry the subscription's resulting status, so read
        # it. This is what flips a user to past_due (and back) promptly.
        parent = (obj.get("parent") or {}).get("subscription_details") or {}
        subscription_id = obj.get("subscription") or parent.get("subscription")
        if subscription_id:
            user = await _find_user(db, {"customer": obj.get("customer")}, subscription_id)
            if user:
                subscription = await _stripe_call(stripe.Subscription.retrieve, subscription_id)
                if not _is_stale_event(user, subscription):
                    _apply_subscription_state(user, subscription)
                    await db.commit()

    return {"status": "success"}
