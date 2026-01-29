"""
Stripe payment endpoints.
"""

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentActiveUser, DBSession
from app.core.config import settings
from app.models.user import User, UserTier

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/create-checkout-session")
async def create_checkout_session(
    user: CurrentActiveUser,
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
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                customer_id = customers.data[0].id
            else:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.full_name,
                    metadata={"user_id": str(user.id)},
                )
                customer_id = customer.id
                # Note: We should ideally save this customer_id to user model here,
                # but we'll do it via webhook or rely on the checkout session to sync it

        checkout_session = stripe.checkout.Session.create(
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: DBSession = Depends(),
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
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle subscription events
    if event["type"] in ["checkout.session.completed", "customer.subscription.updated"]:
        session = event["data"]["object"]

        # Get user ID from client_reference_id (checkout) or metadata (subscription)
        user_id = session.get("client_reference_id")
        if not user_id and "metadata" in session:
            user_id = session["metadata"].get("user_id")

        if user_id:
            user = await db.get(User, user_id)
            if user:
                # Update user subscription info
                if "customer" in session:
                    user.stripe_customer_id = session["customer"]
                if "subscription" in session:
                    user.subscription_id = session["subscription"]

                    # Verify subscription status
                    sub = stripe.Subscription.retrieve(session["subscription"])
                    user.subscription_status = sub.status

                    if sub.status in ["active", "trialing"]:
                        user.tier = UserTier.PRO.value
                    else:
                        # If canceled/unpaid, revert to Free (or handle grace period)
                        user.tier = UserTier.FREE.value

                # For checkout.session.completed specifically
                if event["type"] == "checkout.session.completed":
                    if session.get("payment_status") == "paid":
                        user.tier = UserTier.PRO.value
                        user.subscription_status = "active"  # Assumption for immediate activation

                await db.commit()

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        # Find user with this subscription_id
        stmt = select(User).where(User.subscription_id == subscription["id"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.subscription_status = "canceled"
            user.tier = UserTier.FREE.value
            await db.commit()

    return {"status": "success"}
