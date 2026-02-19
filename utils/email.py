"""Mailblaze-only email utilities.

This module provides a minimal, Mailblaze-focused sending wrapper and a small
sender-resolution helper. Any non-Mailblaze provider support has been removed.
"""

from typing import Optional, Dict
import os
import json
import re
from urllib.parse import urlparse, urlunparse

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

    # Allow Railway or other deploys to set an explicit port via env var.
    # If MAILBLAZE_PORT is set and the base URL doesn't already include a port,
    # append it while preserving scheme and path.
    mb_port = os.getenv("MAILBLAZE_PORT") or os.getenv("Mailblaze_Port")
    if mb_port:
        try:
            parsed = urlparse(base)
            # If netloc already contains a port, leave it.
            if parsed.port is None:
                host = parsed.hostname or parsed.netloc
                if parsed.username and parsed.password:
                    userinfo = f"{parsed.username}:{parsed.password}@"
                elif parsed.username:
                    userinfo = f"{parsed.username}@"
                else:
                    userinfo = ""
                new_netloc = f"{userinfo}{host}:{mb_port}"
                parsed = parsed._replace(netloc=new_netloc)
                base = urlunparse(parsed)
        except Exception:
            # If parsing fails, fall back to the original base unchanged.
            pass

    sender = _get_sender()
    if not sender:
        return {"error": "missing-sender: set SENDER_EMAIL or EMAIL_FROM"}

    payload = {
        "personalizations": [{"to": [{"email": to_addr}]}],
        "from": {"email": sender},
        "subject": subject,
        "from_name": os.getenv("MAILBLAZE_FROM_NAME") or os.getenv("EMAIL_FROM_NAME") or None,
        "subject": subject,
        "body": encoded_html or encoded_plain,
        "plain_text": encoded_plain,
    }

    # Prefer the transactional endpoint first and use the raw `authorization` header
    # Call only the transactional endpoint and send a standard Authorization Bearer header
    endpoints = [f"{base.rstrip('/')}/transactional"]
    headers = {"Authorization": f"Bearer {mb_key}", "Content-Type": "application/x-www-form-urlencoded"}
    last_err = None
    for ep in endpoints:
        try:
            r = requests.post(ep, data=tx_payload, headers=headers, timeout=10)
        endpoints = [f"{base.rstrip('/')}/transactional"]
        headers = {"Authorization": mb_key, "Content-Type": "application/json"}
            except Exception:
                resp_json = {"text": r.text}

                r = requests.post(ep, json=tx_payload, headers=headers, timeout=10)
                return {"ok": True, "provider": "mailblaze", "status_code": r.status_code, "response": resp_json}

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
