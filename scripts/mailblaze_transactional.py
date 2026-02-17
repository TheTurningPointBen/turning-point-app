"""Minimal transactional Mailblaze sender.

Usage (example):

export MAILBLAZE_API_KEY=sk_...
export MAILBLAZE_BASE_URL=https://control.mailblaze.com/api
export EMAIL_FROM=you@domain.com
export EMAIL_FROM_NAME="Your App"
python scripts/mailblaze_transactional.py recipient@example.com "Recipient Name" "Subject" "<h1>HTML body</h1>"

This script intentionally does not print or log the API key.
"""

import base64
import json
import os
import sys
from typing import Optional

import requests


class MailblazeError(RuntimeError):
    pass


def send_mailblaze_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    use_raw_auth: bool = True,
) -> dict:
    """Send a transactional email through Mailblaze.

    - `api_key` and `base_url` default to `MAILBLAZE_API_KEY` and `MAILBLAZE_BASE_URL` env vars.
    - The function encodes the HTML body as base64 (matching your example payload).
    - Returns the response json on success or raises MailblazeError on failure.
    """
    api_key = api_key or os.getenv("MAILBLAZE_API_KEY") or os.getenv("MAILBLAZE_KEY")
    if not api_key:
        raise MailblazeError("Missing MAILBLAZE_API_KEY environment variable")

    base = base_url or os.getenv("MAILBLAZE_BASE_URL") or os.getenv("MAILBLAZE_BASE") or "https://control.mailblaze.com/api"

    from_email = os.getenv("EMAIL_FROM")
    from_name = os.getenv("EMAIL_FROM_NAME") or os.getenv("EMAIL_FROM")
    if not from_email:
        raise MailblazeError("Missing EMAIL_FROM environment variable (sender address)")

    encoded_body = base64.b64encode(html_body.encode("utf-8")).decode("utf-8")

    payload = {
        "to_email": to_email,
        "to_name": to_name,
        "from_email": from_email,
        "from_name": from_name,
        "subject": subject,
        "body": encoded_body,
        # Mailblaze transactional endpoint in this integration expects base64-encoded
        # strings for both the HTML body and the plain text. Encode plain_text too.
        "plain_text": base64.b64encode("Please view this email in HTML format.".encode("utf-8")).decode("utf-8"),
    }

    # Mailblaze examples sometimes show a bare API key header; others use Bearer.
    # Support both: the `use_raw_auth` flag selects the raw `authorization` header
    # (matching your snippet) when True, otherwise use `Bearer <key>` form.
    if use_raw_auth:
        headers = {"authorization": api_key, "Content-Type": "application/json"}
    else:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    url = f"{base.rstrip('/')}/transactional"

    r = requests.post(url, json=payload, headers=headers, timeout=15)

    try:
        body_json = r.json()
    except Exception:
        body_json = {"text": r.text}

    # Match the snippet behaviour: treat 200 or 201 as success.
    if r.status_code not in (200, 201):
        raise MailblazeError(f"Mailblaze error {r.status_code}: {json.dumps(body_json)}")

    return body_json


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python scripts/mailblaze_transactional.py to_email to_name subject html_body")
        sys.exit(2)

    to_email = sys.argv[1]
    to_name = sys.argv[2]
    subject = sys.argv[3]
    html_body = sys.argv[4]

    try:
        res = send_mailblaze_email(to_email, to_name, subject, html_body)
        print("ok", res)
    except MailblazeError as e:
        print("error", str(e))
        sys.exit(1)
