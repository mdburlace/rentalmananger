"""Minimal outgoing email over SMTP (configured with RM_SMTP_* variables)."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from ..config import get_settings

log = logging.getLogger("rentalmanager.email")


def send_email(to: str, subject: str, body: str) -> None:
    s = get_settings()
    if not s.email_enabled:
        raise RuntimeError("Email is not configured (set RM_SMTP_HOST)")
    msg = EmailMessage()
    msg["From"] = s.smtp_from or s.smtp_username
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    security = (s.smtp_security or "starttls").lower()
    ctx = ssl.create_default_context()
    if security == "ssl":
        server = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, context=ctx, timeout=20)
    else:
        server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20)
    with server:
        if security == "starttls":
            server.starttls(context=ctx)
        if s.smtp_username:
            server.login(s.smtp_username, s.smtp_password or "")
        server.send_message(msg)


def send_email_logged(to: str, subject: str, body: str) -> None:
    """Background-task wrapper: never raises, logs failures instead."""
    try:
        send_email(to, subject, body)
        log.info("Sent '%s' email to %s", subject, to)
    except Exception:  # noqa: BLE001
        log.exception("Failed to send '%s' email to %s", subject, to)
