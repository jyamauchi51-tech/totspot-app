"""Tiny helpers: send an email notification, and make a QR code.

Email is config-driven via st.secrets [email]:
    [email]
    host = "smtp.gmail.com"
    port = 587
    user = "you@gmail.com"
    password = "app-password"
    from = "you@gmail.com"
    to   = "megan@example.com"

If [email] is missing/incomplete, send_email() is a graceful no-op so the app
keeps working — nothing breaks, the notification just isn't sent.
"""

from __future__ import annotations

import io
import smtplib
from email.message import EmailMessage

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass


def send_email(cfg: dict, subject: str, body: str) -> tuple[bool, str]:
    if not cfg or not cfg.get("host") or not cfg.get("to"):
        return False, "email not configured"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.get("from") or cfg.get("user", "")
    msg["To"] = cfg["to"]
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg["host"], int(cfg.get("port", 587)), timeout=20) as s:
            s.starttls()
            if cfg.get("user"):
                s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
        return True, "sent"
    except Exception as e:  # noqa: BLE001 - never let email break the app
        return False, str(e)


def qr_png(data: str) -> bytes | None:
    """Return PNG bytes of a QR code for `data`, or None if unavailable."""
    try:
        import qrcode

        img = qrcode.make(data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None
