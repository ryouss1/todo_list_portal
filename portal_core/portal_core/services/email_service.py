"""SMTP email sending service.

Uses Python stdlib smtplib + email.mime (no external dependencies).
When SMTP_HOST is empty, emails are not sent (reset URL logged instead).
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from portal_core import config

logger = logging.getLogger("app.services.email")


def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send an email. Returns True on success, False on failure.

    Does not raise exceptions — failures are logged.
    If SMTP_HOST is not configured, returns False (caller should handle fallback).
    """
    if not config.SMTP_HOST:
        logger.info("SMTP not configured — email not sent to %s (subject: %s)", to, subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM_ADDRESS
    msg["To"] = to

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if config.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
            if config.SMTP_USE_TLS:
                server.starttls()

        if config.SMTP_USERNAME:
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)

        server.sendmail(config.SMTP_FROM_ADDRESS, to, msg.as_string())
        server.quit()
        logger.info("Email sent to %s (subject: %s)", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s (subject: %s)", to, subject)
        return False
