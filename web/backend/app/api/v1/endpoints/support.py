import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.support import SupportRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    """
    Send an email via SMTP.

    Returns True if successful, False otherwise.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Email not sent.")
        return False

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        # Add text and HTML parts
        if text_body:
            part1 = MIMEText(text_body, "plain")
            msg.attach(part1)
        part2 = MIMEText(html_body, "html")
        msg.attach(part2)

        # Create secure SSL context and send
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


@router.post("/contact")
async def contact_support(request: SupportRequest):
    """
    Handle contact support requests.

    Sends an email to the support inbox with the user's message.
    """
    logger.info(f"Support Request Received from {request.email}")
    logger.info(f"Subject: {request.subject}")

    # Build email content
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2563eb;">New Support Request</h2>

        <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">From:</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{request.name} &lt;{request.email}&gt;</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Subject:</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{request.subject}</td>
            </tr>
        </table>

        <h3 style="margin-top: 20px;">Message:</h3>
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #2563eb;">
            {request.message.replace(chr(10), '<br>')}
        </div>

        <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px;">
            This message was sent via the IndexMaker contact form.
        </p>
    </body>
    </html>
    """

    text_body = f"""
New Support Request

From: {request.name} <{request.email}>
Subject: {request.subject}

Message:
{request.message}

---
This message was sent via the IndexMaker contact form.
    """

    # Send email to support inbox
    email_sent = send_email(
        to_email=settings.SUPPORT_EMAIL,
        subject=f"[IndexMaker Support] {request.subject}",
        html_body=html_body,
        text_body=text_body,
    )

    if not email_sent:
        # Log but don't fail - we still received the request
        logger.warning("Email notification could not be sent, but request was logged.")

        # If SMTP is not configured, still return success (we logged it)
        if not settings.SMTP_USER:
            return {
                "status": "success",
                "message": "Support request received (email delivery not configured)",
            }

        # If SMTP is configured but failed, return error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send support request. Please try again or email us directly.",
        )

    return {"status": "success", "message": "Support request sent successfully"}
