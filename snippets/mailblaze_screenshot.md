Mailblaze integration — screenshot-ready snippet

This file is intended for Mailblaze review. Do NOT include your API key in screenshots.

What to show in the screenshot
- The env-var reads for `MAILBLAZE_API_KEY` and `MAILBLAZE_BASE` (or `mailblaze_http`).
- The `Authorization: Bearer {mb_key}` header being set.
- The list of endpoints tried (`/mail/send`, `/v1/mail/send`, `/v1/send`, `/send`).
- The `from` address being resolved via the `_get_sender()` helper.

File location to reference in the app: `utils/email.py`

Code snippet (copy/paste into a single-file screenshot):

```python
# Mailblaze HTTP send snippet (screenshot-ready)
import os
import json
import re
import requests


def _get_sender() -> str:
    candidates = [
        os.getenv("SENDER_EMAIL"),
        os.getenv("EMAIL_FROM"),
        os.getenv("ADMIN_EMAIL"),
    ]
    for c in candidates:
        if not c:
            continue
        if "@" in c:
            m = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", c)
            if m:
                return m.group(1)
            return c
    raise RuntimeError("Missing sender: set SENDER_EMAIL or EMAIL_FROM")


def send_via_mailblaze(to_addr: str, subject: str, body: str, html: str | None = None) -> dict:
    # Read API key and base URL from env (do NOT print the key in screenshots)
    mb_key = os.getenv("MAILBLAZE_API_KEY")
    base = os.getenv("MAILBLAZE_BASE", "https://control.mailblaze.com/api")

    sender = _get_sender()  # resolves Name <email@domain> -> email@domain

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

    for ep in endpoints:
        r = requests.post(ep, data=json.dumps(payload), headers=headers, timeout=10)
        # For screenshots, capture the URL and status code returned here
        print(ep, r.status_code, r.text)
        if r.status_code in (200, 202):
            return {"ok": True}
    return {"error": "mailblaze failed"}


# Example usage (do NOT paste your API key inline):
# export MAILBLAZE_API_KEY=...; export SENDER_EMAIL=you@domain.com
# python -c "from snippet import send_via_mailblaze; print(send_via_mailblaze('recipient@domain.com','Test','Hello'))"
```

Suggested screenshot framing
- Show the snippet lines where `mb_key` and `base` are read (mask the value if the terminal expands envs).
- Show the `headers` assignment with `Authorization: Bearer {mb_key}` visible in code (not the real key).
- Show one of the `endpoints` lines so Mailblaze reviewers can see the attempted endpoint.
- Optionally show a terminal run that prints `https://.../mail/send 202` (mask any API key output).

If you want, I can add this snippet file into the repo (already done) and also create a tiny runnable script `scripts/mailblaze_test.py` that prints masked HTTP responses — would you like me to add and run that now?