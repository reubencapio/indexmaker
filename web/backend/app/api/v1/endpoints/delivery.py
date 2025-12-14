"""
Data Delivery API endpoints (Webhooks, SFTP, Email).
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.delivery import (
    DeliveryLog,
    DeliveryStatus,
    EmailSubscription,
    SFTPDestination,
    WebhookEndpoint,
)
from app.schemas.delivery import (
    DeliveryLogResponse,
    EmailSubscriptionCreate,
    EmailSubscriptionResponse,
    EmailSubscriptionUpdate,
    SFTPCreate,
    SFTPResponse,
    SFTPUpdate,
    WebhookCreate,
    WebhookResponse,
    WebhookUpdate,
)

router = APIRouter()


# ============== WEBHOOKS ==============

@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    db: DBSession,
    current_user: CurrentUser,
) -> list[WebhookEndpoint]:
    """List all webhook endpoints for the current user."""
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.owner_id == current_user.id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    db: DBSession,
    current_user: CurrentUser,
    webhook_in: WebhookCreate,
) -> WebhookEndpoint:
    """Create a new webhook endpoint."""
    webhook = WebhookEndpoint(
        owner_id=current_user.id,
        name=webhook_in.name,
        url=webhook_in.url,
        secret_key=webhook_in.secret_key or secrets.token_hex(32),
        headers=webhook_in.headers,
        events=webhook_in.events,
        index_ids=webhook_in.index_ids,
        max_retries=webhook_in.max_retries,
        retry_delay_seconds=webhook_in.retry_delay_seconds,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    db: DBSession,
    current_user: CurrentUser,
    webhook_id: str,
) -> WebhookEndpoint:
    """Get a specific webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return webhook


@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    db: DBSession,
    current_user: CurrentUser,
    webhook_id: str,
    webhook_in: WebhookUpdate,
) -> WebhookEndpoint:
    """Update a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = webhook_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    
    await db.commit()
    await db.refresh(webhook)
    return webhook


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    db: DBSession,
    current_user: CurrentUser,
    webhook_id: str,
) -> None:
    """Delete a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.delete(webhook)
    await db.commit()


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    db: DBSession,
    current_user: CurrentUser,
    webhook_id: str,
) -> dict:
    """Send a test payload to a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create test payload
    payload = {
        "event": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "message": "This is a test webhook from IndexMaker",
            "webhook_id": webhook_id,
        }
    }
    
    # Sign payload
    payload_str = json.dumps(payload, sort_keys=True)
    if webhook.secret_key:
        signature = hmac.new(
            webhook.secret_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
    else:
        signature = None
    
    headers = webhook.headers or {}
    headers["Content-Type"] = "application/json"
    if signature:
        headers["X-Webhook-Signature"] = signature
    
    # Send request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook.url,
                content=payload_str,
                headers=headers,
            )
        
        # Log the delivery
        log = DeliveryLog(
            delivery_type="webhook",
            destination_id=webhook_id,
            status=DeliveryStatus.SUCCESS.value if response.is_success else DeliveryStatus.FAILED.value,
            payload_summary="Test webhook",
            response_code=response.status_code,
            response_body=response.text[:500] if response.text else None,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(log)
        
        # Update webhook stats
        webhook.total_deliveries += 1
        webhook.last_triggered_at = datetime.now(timezone.utc)
        if response.is_success:
            webhook.successful_deliveries += 1
            webhook.last_success_at = datetime.now(timezone.utc)
        else:
            webhook.last_failure_at = datetime.now(timezone.utc)
            webhook.last_error = f"HTTP {response.status_code}"
        
        await db.commit()
        
        return {
            "success": response.is_success,
            "status_code": response.status_code,
            "response": response.text[:500] if response.text else None,
        }
        
    except Exception as e:
        webhook.last_failure_at = datetime.now(timezone.utc)
        webhook.last_error = str(e)
        await db.commit()
        
        return {
            "success": False,
            "error": str(e),
        }


# ============== SFTP ==============

@router.get("/sftp", response_model=list[SFTPResponse])
async def list_sftp_destinations(
    db: DBSession,
    current_user: CurrentUser,
) -> list[SFTPDestination]:
    """List all SFTP destinations for the current user."""
    result = await db.execute(
        select(SFTPDestination)
        .where(SFTPDestination.owner_id == current_user.id)
        .order_by(SFTPDestination.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/sftp", response_model=SFTPResponse, status_code=status.HTTP_201_CREATED)
async def create_sftp_destination(
    db: DBSession,
    current_user: CurrentUser,
    sftp_in: SFTPCreate,
) -> SFTPDestination:
    """Create a new SFTP destination."""
    sftp = SFTPDestination(
        owner_id=current_user.id,
        name=sftp_in.name,
        host=sftp_in.host,
        port=sftp_in.port,
        username=sftp_in.username,
        password=sftp_in.password,  # TODO: Encrypt before storing
        private_key=sftp_in.private_key,  # TODO: Encrypt before storing
        remote_path=sftp_in.remote_path,
        frequency=sftp_in.frequency,
        schedule_time=sftp_in.schedule_time,
        schedule_day=sftp_in.schedule_day,
        index_ids=sftp_in.index_ids,
        file_format=sftp_in.file_format,
        include_history=sftp_in.include_history,
    )
    db.add(sftp)
    await db.commit()
    await db.refresh(sftp)
    return sftp


@router.get("/sftp/{sftp_id}", response_model=SFTPResponse)
async def get_sftp_destination(
    db: DBSession,
    current_user: CurrentUser,
    sftp_id: str,
) -> SFTPDestination:
    """Get a specific SFTP destination."""
    result = await db.execute(
        select(SFTPDestination).where(SFTPDestination.id == sftp_id)
    )
    sftp = result.scalar_one_or_none()
    
    if not sftp:
        raise HTTPException(status_code=404, detail="SFTP destination not found")
    if sftp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return sftp


@router.patch("/sftp/{sftp_id}", response_model=SFTPResponse)
async def update_sftp_destination(
    db: DBSession,
    current_user: CurrentUser,
    sftp_id: str,
    sftp_in: SFTPUpdate,
) -> SFTPDestination:
    """Update an SFTP destination."""
    result = await db.execute(
        select(SFTPDestination).where(SFTPDestination.id == sftp_id)
    )
    sftp = result.scalar_one_or_none()
    
    if not sftp:
        raise HTTPException(status_code=404, detail="SFTP destination not found")
    if sftp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = sftp_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sftp, field, value)
    
    await db.commit()
    await db.refresh(sftp)
    return sftp


@router.delete("/sftp/{sftp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sftp_destination(
    db: DBSession,
    current_user: CurrentUser,
    sftp_id: str,
) -> None:
    """Delete an SFTP destination."""
    result = await db.execute(
        select(SFTPDestination).where(SFTPDestination.id == sftp_id)
    )
    sftp = result.scalar_one_or_none()
    
    if not sftp:
        raise HTTPException(status_code=404, detail="SFTP destination not found")
    if sftp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.delete(sftp)
    await db.commit()


@router.post("/sftp/{sftp_id}/test")
async def test_sftp_connection(
    db: DBSession,
    current_user: CurrentUser,
    sftp_id: str,
) -> dict:
    """Test SFTP connection."""
    result = await db.execute(
        select(SFTPDestination).where(SFTPDestination.id == sftp_id)
    )
    sftp = result.scalar_one_or_none()
    
    if not sftp:
        raise HTTPException(status_code=404, detail="SFTP destination not found")
    if sftp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        import asyncssh
        
        async with asyncssh.connect(
            host=sftp.host,
            port=sftp.port,
            username=sftp.username,
            password=sftp.password,
            known_hosts=None,
            connect_timeout=10,
        ) as conn:
            async with conn.start_sftp_client() as sftp_client:
                # Try to list the remote directory
                await sftp_client.listdir(sftp.remote_path)
        
        return {"success": True, "message": "SFTP connection successful"}
    except ImportError:
        return {"success": False, "error": "asyncssh not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== EMAIL ==============

@router.get("/email", response_model=list[EmailSubscriptionResponse])
async def list_email_subscriptions(
    db: DBSession,
    current_user: CurrentUser,
) -> list[EmailSubscription]:
    """List all email subscriptions for the current user."""
    result = await db.execute(
        select(EmailSubscription)
        .where(EmailSubscription.owner_id == current_user.id)
        .order_by(EmailSubscription.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/email", response_model=EmailSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_email_subscription(
    db: DBSession,
    current_user: CurrentUser,
    email_in: EmailSubscriptionCreate,
) -> EmailSubscription:
    """Create a new email subscription."""
    subscription = EmailSubscription(
        owner_id=current_user.id,
        name=email_in.name,
        recipients=email_in.recipients,
        frequency=email_in.frequency,
        schedule_time=email_in.schedule_time,
        schedule_day=email_in.schedule_day,
        index_ids=email_in.index_ids,
        report_type=email_in.report_type,
        include_attachments=email_in.include_attachments,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


@router.get("/email/{subscription_id}", response_model=EmailSubscriptionResponse)
async def get_email_subscription(
    db: DBSession,
    current_user: CurrentUser,
    subscription_id: str,
) -> EmailSubscription:
    """Get a specific email subscription."""
    result = await db.execute(
        select(EmailSubscription).where(EmailSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Email subscription not found")
    if subscription.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return subscription


@router.patch("/email/{subscription_id}", response_model=EmailSubscriptionResponse)
async def update_email_subscription(
    db: DBSession,
    current_user: CurrentUser,
    subscription_id: str,
    email_in: EmailSubscriptionUpdate,
) -> EmailSubscription:
    """Update an email subscription."""
    result = await db.execute(
        select(EmailSubscription).where(EmailSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Email subscription not found")
    if subscription.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = email_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)
    
    await db.commit()
    await db.refresh(subscription)
    return subscription


@router.delete("/email/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_subscription(
    db: DBSession,
    current_user: CurrentUser,
    subscription_id: str,
) -> None:
    """Delete an email subscription."""
    result = await db.execute(
        select(EmailSubscription).where(EmailSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Email subscription not found")
    if subscription.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.delete(subscription)
    await db.commit()


# ============== DELIVERY LOGS ==============

@router.get("/logs", response_model=list[DeliveryLogResponse])
async def list_delivery_logs(
    db: DBSession,
    current_user: CurrentUser,
    delivery_type: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[DeliveryLog]:
    """List recent delivery logs."""
    # Get user's destinations
    webhooks = await db.execute(
        select(WebhookEndpoint.id).where(WebhookEndpoint.owner_id == current_user.id)
    )
    sftp_dests = await db.execute(
        select(SFTPDestination.id).where(SFTPDestination.owner_id == current_user.id)
    )
    email_subs = await db.execute(
        select(EmailSubscription.id).where(EmailSubscription.owner_id == current_user.id)
    )
    
    destination_ids = (
        [r[0] for r in webhooks.fetchall()] +
        [r[0] for r in sftp_dests.fetchall()] +
        [r[0] for r in email_subs.fetchall()]
    )
    
    if not destination_ids:
        return []
    
    query = (
        select(DeliveryLog)
        .where(DeliveryLog.destination_id.in_(destination_ids))
        .order_by(DeliveryLog.started_at.desc())
        .limit(limit)
    )
    
    if delivery_type:
        query = query.where(DeliveryLog.delivery_type == delivery_type)
    
    result = await db.execute(query)
    return list(result.scalars().all())

