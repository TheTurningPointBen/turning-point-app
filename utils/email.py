"""Email utilities.

This module prefers Mailblaze HTTP when configured. Set `EMAIL_PROVIDER=mailblaze` to force
Mailblaze-only behaviour. If Mailblaze is chosen but the Mailblaze API key/base are missing
the functions return clear Mailblaze-specific errors instead of attempting SMTP.
"""

from typing import Optional, Dict
import os
import json
import requests
import re


def _send_via_mailblaze(to_addr: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
    mb_key = (
        os.getenv("MAILBLAZE_API_KEY")
        or os.getenv("MAILBLAZE_KEY")
        or os.getenv("mailblaze_api_key")
        or os.getenv("MAILBLAZE_APIKEY")
    )
    if not mb_key:
        return {"error": "no-mailblaze-key"}
    base = (
        os.getenv("MAILBLAZE_BASE")
        or os.getenv("MAILBLAZE_BASE_URL")
        or os.getenv("mailblaze_http")
        or os.getenv("MAILBLAZE_BASEURL")
        or "https://control.mailblaze.com/api"
    )
    sender = _get_sender()
    if not sender:
        return {"error": "Missing sender address: set SENDER_EMAIL or EMAIL_FROM (case-sensitive) to a valid email"}

    payload = {
        "personalizations": [{"to": [{"email": to_addr}]}],
        "from": {"email": sender},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body or ""}],
    }
    if html:
        payload["content"].append({"type": "text/html", "value": html})

    headers = {"Authorization": f"Bearer {mb_key}", "Content-Type": "application/json"}
    endpoints = [f"{base}/mail/send", f"{base}/v1/mail/send", f"{base}/v1/send", f"{base}/send"]
    last_err = None
    for ep in endpoints:
        try:
            r = requests.post(ep, data=json.dumps(payload), headers=headers, timeout=10)
            if r.status_code in (200, 202):
                return {"ok": True}
            last_err = f"{ep} -> {r.status_code} {r.text}"
        except Exception as e:
            last_err = repr(e)
    return {"error": f"mailblaze: {last_err}"}


def _get_sender() -> Optional[str]:
    """Find a sender email from common env var names (case-insensitive variants).

    Returns the first value that contains an email address. Accepts values like
    'Name <email@domain>' and extracts the email. Returns None if no usable sender.
    """
    candidates = [
        os.getenv("SENDER_EMAIL"),
        os.getenv("sender_email"),
        os.getenv("EMAIL_FROM"),
        os.getenv("email_from"),
        os.getenv("SMTP_USER"),
        os.getenv("ADMIN_EMAIL"),
    ]
    for c in candidates:
        if not c:
            continue
        c = c.strip()
        if "@" in c:
            # If it's a display name with an embedded email, extract it
            m = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", c)
            if m:
                return m.group(1)
            # Otherwise assume the whole string is an email-like value
            return c
    return None


def _send_via_sendgrid(to_addr: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
    sg_key = os.getenv("SENDGRID_API_KEY")
    if not sg_key:
        return {"error": "no-sendgrid-key"}
    from_email = _get_sender()
    if not from_email:
        return {"error": "Missing sender address: set SENDER_EMAIL or EMAIL_FROM to a valid email"}

    content = []
    if body:
        content.append({"type": "text/plain", "value": body})
    if html:
        content.append({"type": "text/html", "value": html})

    payload = {
        "personalizations": [{"to": [{"email": to_addr}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": content or [{"type": "text/plain", "value": ""}],
    }
    headers = {"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"}
    try:
        r = requests.post("https://api.sendgrid.com/v3/mail/send", data=json.dumps(payload), headers=headers, timeout=10)
        if r.status_code in (200, 202):
            return {"ok": True}
        return {"error": f"sendgrid: {r.status_code} {r.text}"}
    except Exception as e:
        return {"error": f"sendgrid: {repr(e)}"}


def send_email(to_email: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
    """Send an email. Mailblaze is preferred when configured or when EMAIL_PROVIDER=mailblaze.

    Behaviour:
    - If `EMAIL_PROVIDER=mailblaze` is set: only attempt Mailblaze and return Mailblaze-specific errors.
    - If Mailblaze API key is present and EMAIL_PROVIDER is not 'sendgrid': try Mailblaze first and return its result.
    - Otherwise, fall back to SendGrid (if configured) then return an aggregated error.
    """
    provider = (os.getenv("EMAIL_PROVIDER") or "").lower()

    mb_key_present = bool(
        os.getenv("MAILBLAZE_API_KEY") or os.getenv("MAILBLAZE_KEY") or os.getenv("mailblaze_api_key")
    )

    # If user explicitly requested mailblaze-only, enforce it
    if provider == "mailblaze":
        if not mb_key_present:
            return {"error": "Missing Mailblaze configuration (MAILBLAZE_API_KEY or mailblaze_api_key)"}
        return _send_via_mailblaze(to_email, subject, body, html=html)

    # If Mailblaze is available and the user hasn't explicitly forced SendGrid,
    # use Mailblaze only (do not fall back to other providers).
    if mb_key_present and provider != "sendgrid":
        return _send_via_mailblaze(to_email, subject, body, html=html)

    # Otherwise, try SendGrid (if configured) and return its result.
    sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
    if sg_res.get("ok"):
        return {"ok": True}

    # If we get here and Mailblaze was configured but provider explicitly set to sendgrid failed,
    # return a clear aggregated message.
    if mb_key_present:
        return {"error": f"sendgrid: {sg_res.get('error')} ; mailblaze: available but not selected or failed"}
    return {"error": f"sendgrid: {sg_res.get('error')} ; mailblaze: missing"}


def send_admin_email(subject: str, body: str, admin_email: Optional[str] = None) -> Dict:
    """Send an email to admin. Uses same provider preference as `send_email`.
    """
    sender = _get_sender()
    admin = admin_email or os.getenv("ADMIN_EMAIL") or sender
    if not admin:
        return {"error": "no-admin-email"}
    return send_email(admin, subject, body)


def send_mailgun_email(to_email: str, subject: str, text: Optional[str] = None, html: Optional[str] = None) -> Dict:
    body = text or ""
    try:
        return send_email(to_email, subject, body, html=html)
    except Exception as e:
        return {"error": repr(e)}

