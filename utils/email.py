"""Mailblaze-only email utilities.

This module provides a minimal, Mailblaze-focused sending wrapper and a small
sender-resolution helper. Any non-Mailblaze provider support has been removed.
"""

from typing import Optional, Dict
import os
import json
import re
import requests


def _get_sender() -> Optional[str]:
    """Resolve a usable sender email from common environment variables.

    Accepts values like 'Name <email@domain>' and extracts the email. Returns
    the first valid-looking email or None if none found.
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
            m = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", c)
            if m:
                return m.group(1)
            return c
    return None


def _send_via_mailblaze(to_addr: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
    """Send email via Mailblaze HTTP API.

    Looks for `MAILBLAZE_API_KEY` and `MAILBLAZE_BASE` (or `mailblaze_http`).
    Tries common Mailblaze endpoints and returns a dict with `{'ok': True}` on success
    or `{'error': '...'}'` on failure.
    """
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
        return {"error": "missing-sender: set SENDER_EMAIL or EMAIL_FROM"}

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


def send_email(to_email: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
    """Send an email using Mailblaze only.

    Returns `{'ok': True}` on success or `{'error': '...'}'` on failure. This function
    no longer attempts any other provider.
    """
    mb_key_present = bool(
        os.getenv("MAILBLAZE_API_KEY") or os.getenv("MAILBLAZE_KEY") or os.getenv("mailblaze_api_key")
    )
    if not mb_key_present:
        return {"error": "Missing Mailblaze configuration (MAILBLAZE_API_KEY)"}
    return _send_via_mailblaze(to_email, subject, body, html=html)


def send_admin_email(subject: str, body: str, admin_email: Optional[str] = None) -> Dict:
    """Send an email to admin via Mailblaze.

    If `admin_email` is not provided this will use the resolved sender or the
    `ADMIN_EMAIL` env var as the destination.
    """
    admin = admin_email or os.getenv("ADMIN_EMAIL") or _get_sender()
    if not admin:
        return {"error": "no-admin-email"}
    return send_email(admin, subject, body)

