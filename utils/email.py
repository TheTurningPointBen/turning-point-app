import os
import smtplib
from email.message import EmailMessage
import json
import requests

def send_admin_email(subject: str, body: str, admin_email: str | None = None) -> dict:
    """Send a plain-text email to the admin using SMTP credentials from env.

    Expects the following env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ADMIN_EMAIL
    Returns dict with either {'ok': True} or {'error': 'message'}
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS")
    sender_name = os.getenv("SENDER_NAME")
    sender_email = os.getenv("EMAIL_FROM") or os.getenv("SENDER_EMAIL") or user
    admin = admin_email or os.getenv("ADMIN_EMAIL") or sender_email

    if not (host and user and password and admin):
        return {"error": "Missing SMTP configuration or admin email"}

    msg = EmailMessage()
    msg["Subject"] = subject
    if sender_name:
        msg["From"] = f"{sender_name} <{sender_email}>"
    else:
        msg["From"] = sender_email
    msg["To"] = admin
    msg.set_content(body)

    try:
        # Try plain SMTP with STARTTLS first (common on port 587)
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            try:
                smtp.starttls()
            except Exception:
                # Server may not support STARTTLS; continue
                pass
            smtp.login(user, password)
            smtp.send_message(msg)
        return {"ok": True}
    except Exception as e:
        # Fallback: try implicit TLS (SMTPS) on port 465 if different
        try:
            if port != 465:
                with smtplib.SMTP_SSL(host, 465, timeout=30) as smtp:
                    smtp.login(user, password)
                    smtp.send_message(msg)
                return {"ok": True}
        except Exception:
            pass
        # Try SendGrid API fallback if available
        sg_key = os.getenv("SENDGRID_API_KEY")
        if sg_key:
            try:
                from_email = os.getenv("SENDER_EMAIL") or user
                sender_name = os.getenv("SENDER_NAME")
                payload = {
                    "personalizations": [{"to": [{"email": admin}]}],
                    "from": {"email": from_email},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                }
                if sender_name:
                    payload["from"]["name"] = sender_name
                headers = {"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"}
                r = requests.post("https://api.sendgrid.com/v3/mail/send", data=json.dumps(payload), headers=headers, timeout=10)
                if r.status_code in (200, 202):
                    return {"ok": True}
                return {"error": f"SendGrid error: {r.status_code} {r.text}"}
            except Exception as se:
                return {"error": f"SMTP error: {repr(e)}; SendGrid error: {repr(se)}"}
        return {"error": repr(e)}


# Mailgun helper removed: Mailgun is no longer used. SMTP (Gmail) is preferred.



def send_email(to_email: str, subject: str, body: str, html: str | None = None) -> dict:
    """Send an email to `to_email` using SMTP credentials from env.

    Accepts plain `body` and optional `html`. Expects env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD|SMTP_PASS, EMAIL_FROM|SENDER_EMAIL
    Returns {'ok': True} or {'error': 'message'}
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS")
    sender_name = os.getenv("SENDER_NAME")
    sender_email = os.getenv("EMAIL_FROM") or os.getenv("SENDER_EMAIL") or user

    if not (host and user and password and to_email):
        return {"error": "Missing SMTP configuration or recipient email"}

    msg = EmailMessage()
    msg["Subject"] = subject
    if sender_name:
        msg["From"] = f"{sender_name} <{sender_email}>"
    else:
        msg["From"] = sender_email
    msg["To"] = to_email
    # Plain text body
    msg.set_content(body or "")
    # Optional HTML alternative
    if html:
        try:
            msg.add_alternative(html, subtype="html")
        except Exception:
            pass

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            try:
                smtp.starttls()
            except Exception:
                pass
            smtp.login(user, password)
            smtp.send_message(msg)
        return {"ok": True}
    except Exception as e:
        try:
            if port != 465:
                with smtplib.SMTP_SSL(host, 465, timeout=30) as smtp:
                    smtp.login(user, password)
                    smtp.send_message(msg)
                return {"ok": True}
        except Exception:
            pass
        # Try SendGrid API fallback if available
        sg_key = os.getenv("SENDGRID_API_KEY")
        if sg_key:
            try:
                from_email = os.getenv("SENDER_EMAIL") or user
                sender_name = os.getenv("SENDER_NAME")
                payload = {
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": from_email},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                }
                if sender_name:
                    payload["from"]["name"] = sender_name
                headers = {"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"}
                r = requests.post("https://api.sendgrid.com/v3/mail/send", data=json.dumps(payload), headers=headers, timeout=10)
                if r.status_code in (200, 202):
                    return {"ok": True}
                return {"error": f"SendGrid error: {r.status_code} {r.text}"}
            except Exception as se:
                return {"error": f"SMTP error: {repr(e)}; SendGrid error: {repr(se)}"}
        return {"error": repr(e)}


# Backwards compatibility: some deployed pages may still import `send_mailgun_email`.
def send_mailgun_email(to_email: str, subject: str, text: str | None = None, html: str | None = None) -> dict:
    """Compatibility wrapper: route old Mailgun calls to SMTP `send_email`.

    Accepts `text` and `html` like the old helper and forwards to `send_email`.
    """
    # Prefer html if provided, otherwise use text as plain body
    body = text or ""
    try:
        return send_email(to_email, subject, body, html=html)
    except Exception as e:
        return {"error": repr(e)}
