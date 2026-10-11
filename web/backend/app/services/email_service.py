"""
Outbound email.

One sender for every message the app produces, and one layout so they look like
they came from the same product.
"""

from __future__ import annotations

import html
import logging
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)

# (file name, content, MIME subtype)
Attachment = tuple[str, bytes, str]


def is_configured() -> bool:
    return bool(settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    *,
    attachments: list[Attachment] | None = None,
    unsubscribe_url: str | None = None,
) -> bool:
    """
    Send an email via SMTP. Blocking: call it off the event loop.

    Returns True if the message was handed to the server, False otherwise.
    """
    if not is_configured():
        logger.warning("SMTP credentials not configured. Email not sent.")
        return False

    try:
        body = MIMEMultipart("alternative")
        if text_body:
            body.attach(MIMEText(text_body, "plain"))
        body.attach(MIMEText(html_body, "html"))

        msg: MIMEMultipart = body
        if attachments:
            msg = MIMEMultipart("mixed")
            msg.attach(body)
            for filename, content, subtype in attachments:
                part = MIMEApplication(content, _subtype=subtype)
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)

        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        if unsubscribe_url:
            # Lets mail clients show their own unsubscribe button.
            msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def button(label: str, url: str) -> str:
    return (
        f'<p style="margin:24px 0"><a href="{html.escape(url, quote=True)}" '
        'style="background:#2563eb;color:#ffffff;text-decoration:none;padding:10px 18px;'
        f'border-radius:8px;font-weight:600;display:inline-block">{html.escape(label)}</a></p>'
    )


def layout(title: str, body_html: str, footer_html: str = "") -> str:
    """Wrap message content in the shared email frame. `body_html` is trusted."""
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:24px;background:#f4f5f7;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;color:#111827">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:28px">
    <p style="margin:0 0 20px;font-weight:700;color:#2563eb">IndexMaker</p>
    <h1 style="margin:0 0 16px;font-size:20px;line-height:1.3">{html.escape(title)}</h1>
    {body_html}
  </div>
  <div style="max-width:600px;margin:12px auto 0;font-size:12px;line-height:1.5;color:#6b7280;text-align:center">
    {footer_html}
    <p style="margin:8px 0 0">For research and information only; not investment advice.</p>
  </div>
</body>
</html>"""
