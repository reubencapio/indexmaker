"""
Stripe payment endpoints.
"""

import asyncio
import logging
from typing import Any

import stripe
from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentActiveUser, DBSession
from app.core.config import settings
from app.models.user import User, UserTier

logger = logging.getLogger(__name__)

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

# The Stripe SDK is synchronous, so every call is pushed to a worker thread;
# calling it inline would block the event loop for the whole round-trip.
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


async def _stripe_call(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking Stripe SDK call without stalling the event loop."""
    return await asyncio.to_thread(lambda: func(*args, **kwargs))


@router.post("/create-checkout-session")
async def create_checkout_session(
    user: CurrentActiveUser,
    db: DBSession,
) -> dict:
    """
    Create a Stripe Checkout Session for Pro subscription.
    """
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRO_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment configuration missing",
        )

    try:
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

        checkout_session = await _stripe_call(
            stripe.checkout.Session.create,
            customer=customer_id,
            client_reference_id=str(user.id),
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.STRIPE_PRO_PRICE_ID,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/payment/cancel",
            subscription_data={
                "metadata": {"user_id": str(user.id)},
            },
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


async def _apply_subscription_state(user: User, subscription: Any) -> None:
    """Sync a user's tier and subscription fields from a Stripe subscription."""
    user.subscription_id = subscription["id"]
    user.subscription_status = subscription["status"]
    if subscription["status"] in ACTIVE_SUBSCRIPTION_STATUSES:
        user.tier = UserTier.PRO.value
    else:
        user.tier = UserTier.FREE.value


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: DBSession,
    stripe_signature: str = Header(None),
):
    """
    Stripe webhook handler.
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
        user_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id")
        user = await db.get(User, user_id) if user_id else None
        if user:
            if obj.get("customer"):
                user.stripe_customer_id = obj["customer"]

            subscription_id = obj.get("subscription")
            if subscription_id:
                # Trust the subscription's own status rather than assuming active.
                subscription = await _stripe_call(stripe.Subscription.retrieve, subscription_id)
                await _apply_subscription_state(user, subscription)
            elif obj.get("payment_status") == "paid":
                user.tier = UserTier.PRO.value
                user.subscription_status = "active"

            await db.commit()

    elif event_type == "customer.subscription.updated":
        # `obj` IS the subscription here -- its id and status live at the top
        # level, not under a "subscription" key. Reading it as if it were a
        # checkout session meant plan changes and renewals were silently ignored.
        user_id = (obj.get("metadata") or {}).get("user_id")
        user = await db.get(User, user_id) if user_id else None
        if user is None:
            result = await db.execute(select(User).where(User.subscription_id == obj["id"]))
            user = result.scalar_one_or_none()

        if user:
            if obj.get("customer"):
                user.stripe_customer_id = obj["customer"]
            await _apply_subscription_state(user, obj)
            await db.commit()

    elif event_type == "customer.subscription.deleted":
        result = await db.execute(select(User).where(User.subscription_id == obj["id"]))
        user = result.scalar_one_or_none()

        if user:
            user.subscription_status = "canceled"
            user.tier = UserTier.FREE.value
            await db.commit()

    return {"status": "success"}
