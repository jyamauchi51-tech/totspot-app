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


def branded_email(heading: str, message: str, button_url: str,
                  website_url: str, contact: dict,
                  button_label: str = "Open Parent Portal &rarr;") -> str:
    """A professional, on-brand HTML email body (logo referenced by cid 'totspotlogo')."""
    coral, ink, muted = "#F4978E", "#2B2B2B", "#8A94A6"
    rainbow = "linear-gradient(90deg,#F4978E,#F6B26B,#FCE38A,#A8DB8F,#9FE0DF,#C9A7E9)"
    bits = [contact.get("name"), contact.get("phone"), contact.get("email")]
    contact_line = " &nbsp;·&nbsp; ".join(b for b in bits if b)
    return f"""\
<div style="background:#FFFAF6;padding:24px 0;font-family:Arial,Helvetica,sans-serif;">
 <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #ECEFF4;">
   <tr><td style="height:8px;background:{rainbow};line-height:8px;font-size:0;">&nbsp;</td></tr>
   <tr><td align="center" style="padding:22px 24px 4px;">
     <img src="cid:totspotlogo" alt="The Tot Spot" width="240" style="max-width:240px;width:70%;height:auto;display:block;">
   </td></tr>
   <tr><td style="padding:8px 34px 4px;">
     <h1 style="font-size:22px;color:{ink};margin:0 0 10px;text-align:center;font-weight:800;">{heading}</h1>
     <p style="font-size:16px;color:{ink};line-height:1.55;margin:0 0 22px;text-align:center;">{message}</p>
     <div style="text-align:center;margin:0 0 26px;">
       <a href="{button_url}" style="display:inline-block;background:{coral};color:#ffffff;text-decoration:none;font-weight:bold;padding:13px 30px;border-radius:999px;font-size:16px;">{button_label}</a>
     </div>
   </td></tr>
   <tr><td style="background:#FDEBE8;padding:18px 24px;text-align:center;">
     <p style="margin:0 0 6px;font-size:13px;color:{muted};">{contact_line}</p>
     <p style="margin:0 0 8px;font-size:13px;"><a href="{website_url}" style="color:{coral};text-decoration:none;font-weight:bold;">Visit our website</a></p>
     <p style="margin:0;font-size:11px;color:{muted};line-height:1.5;">📲 Tip: add The Tot Spot to your home screen — iPhone: Share &rarr; Add to Home Screen &nbsp;·&nbsp; Android: &#8942; &rarr; Add to Home screen</p>
   </td></tr>
  </table>
  <p style="font-size:11px;color:#B0B6C0;margin:14px 0 0;">The Tot Spot &middot; Preschool Prep &middot; Surprise, AZ</p>
 </td></tr></table>
</div>"""


def fetch(url: str):
    """Download bytes from a URL (e.g. an Airtable attachment). None on failure."""
    try:
        import requests
        r = requests.get(url, timeout=25)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def send_email(cfg: dict, subject: str, body: str, to: str | None = None,
               attachments: list | None = None, html: str | None = None,
               inline_images: list | None = None) -> tuple[bool, str]:
    recipient = to or (cfg.get("to") if cfg else None)
    if not cfg or not cfg.get("host") or not recipient:
        return False, "email not configured"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.get("from") or cfg.get("user", "")
    msg["To"] = recipient
    msg.set_content(body)  # plain-text fallback
    if html:
        msg.add_alternative(html, subtype="html")
        html_part = msg.get_payload()[-1]
        for cid, content, subtype in (inline_images or []):
            if content:
                html_part.add_related(content, maintype="image", subtype=subtype, cid=cid)
    import mimetypes
    for filename, content in (attachments or []):
        if not content:
            continue
        ctype, _ = mimetypes.guess_type(filename)
        maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
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
