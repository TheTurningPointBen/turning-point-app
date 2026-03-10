"""Mailblaze-only email utilities.

This module provides a minimal, Mailblaze-focused sending wrapper and a small
sender-resolution helper. Any non-Mailblaze provider support has been removed.
"""

from typing import Optional, Dict
import os
import json
import re
from html import escape
from urllib.parse import urlparse, urlunparse

import requests
import base64


EMAIL_SIGN_OFF_PLAIN = (
    "Thank you for your booking.\n"
    "Please feel free to contact admin@theturningpoint.co.za if you have any concerns.\n\n"
    "Kind Regards\n"
    "The Turning Point Team"
)

EMAIL_SIGN_OFF_HTML = (
    "<p>Thank you for your booking.<br>"
    "Please feel free to contact admin@theturningpoint.co.za if you have any concerns.</p>"
    "<p>Kind Regards<br>"
    "The Turning Point Team</p>"
)


def _with_sign_off(text: Optional[str]) -> str:
    """Append the standard sign-off once to plain-text email content."""
    base = (text or "").rstrip()
    if "The Turning Point Team" in base and "admin@theturningpoint.co.za" in base:
        return base
    if not base:
        return EMAIL_SIGN_OFF_PLAIN
    return f"{base}\n\n{EMAIL_SIGN_OFF_PLAIN}"


def _with_sign_off_html(html: Optional[str]) -> Optional[str]:
    """Append the standard sign-off once to HTML email content."""
    if html is None:
        return None
    base = html.rstrip()
    if "The Turning Point Team" in base and "admin@theturningpoint.co.za" in base:
        return base
    if not base:
        return EMAIL_SIGN_OFF_HTML
    return f"{base}<br><br>{EMAIL_SIGN_OFF_HTML}"


def _plain_to_html(text: Optional[str]) -> str:
    """Convert plain text into minimal, safe HTML while preserving line breaks."""
    plain = (text or "").strip()
    if not plain:
        return ""
    return escape(plain).replace("\n", "<br>")


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
        os.getenv("API_KEY")
        or os.getenv("MAILBLAZE_API_KEY")
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

    # Allow Render or other deploys to set an explicit port via env var.
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

    # Build minimal transactional JSON payload — only include non-empty body fields
    html_body = html if html is not None else _plain_to_html(body)
    encoded_body = base64.b64encode((html_body or "").encode("utf-8")).decode("utf-8")
    encoded_plain = base64.b64encode((body or "").encode("utf-8")).decode("utf-8")

    tx_payload = {
        "to_email": to_addr,
        "to_name": None,
        "from_email": sender,
        "from_name": os.getenv("MAILBLAZE_FROM_NAME") or os.getenv("EMAIL_FROM_NAME") or None,
        "subject": subject,
    }

    # Mailblaze treats empty strings as missing; only send keys when non-empty
    if encoded_body:
        tx_payload["body"] = encoded_body
    if encoded_plain:
        tx_payload["plain_text"] = encoded_plain

    endpoints = [f"{base.rstrip('/')}/transactional"]
    headers = {"Authorization": mb_key, "Content-Type": "application/json"}
    last_err = None
    for ep in endpoints:
        try:
            r = requests.post(ep, json=tx_payload, headers=headers, timeout=10)
            try:
                resp_json = r.json()
            except Exception:
                resp_json = {"text": r.text}

            if r.status_code in (200, 201, 202):
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

    body_with_sign_off = _with_sign_off(body)
    html_with_sign_off = _with_sign_off_html(html)
    return _send_via_mailblaze(to_email, subject, body_with_sign_off, html=html_with_sign_off)


def send_admin_email(subject: str, body: str, admin_email: Optional[str] = None) -> Dict:
    """Send an email to admin via Mailblaze.

    If `admin_email` is not provided this will use the `ADMIN_EMAIL` env var,
    then fall back to the shared admin inbox.
    """
    admin = admin_email or os.getenv("ADMIN_EMAIL") or "admin@theturningpoint.co.za"
    if not admin:
        return {"error": "no-admin-email"}
    return send_email(admin, subject, body)
