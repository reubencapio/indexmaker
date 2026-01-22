import logging

from fastapi import APIRouter

from app.schemas.support import SupportRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/contact")
async def contact_support(request: SupportRequest):
    """
    Handle contact support requests.
    In a real app, this would send an email via SendGrid/SES.
    For now, we just log it.
    """
    logger.info(f"Support Request Received from {request.email}")
    logger.info(f"Subject: {request.subject}")
    logger.info(f"Message: {request.message}")

    return {"status": "success", "message": "Support request received"}
