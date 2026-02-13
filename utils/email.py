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
    password = os.getenv("SMTP_PASS")
    sender_name = os.getenv("SENDER_NAME")
    sender_email = os.getenv("SENDER_EMAIL") or user
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
        # Try Mailgun HTTP API if configured
        mg_key = os.getenv("MAILGUN_API_KEY")
        mg_domain = os.getenv("MAILGUN_DOMAIN")
        if mg_key and mg_domain:
            try:
                from_email = os.getenv("SENDER_EMAIL") or user
                sender_name = os.getenv("SENDER_NAME")
                mg_from = f"{sender_name} <{from_email}>" if sender_name else from_email
                mg_url = f"https://api.mailgun.net/v3/{mg_domain}/messages"
                data = {"from": mg_from, "to": admin, "subject": subject, "text": body}
                r = requests.post(mg_url, auth=("api", mg_key), data=data, timeout=10)
                if r.status_code in (200, 202):
                    return {"ok": True}
                return {"error": f"Mailgun error: {r.status_code} {r.text}"}
            except Exception as me:
                # Fall through to SendGrid fallback if available
                mg_err = repr(me)
        else:
            mg_err = None

        # If SendGrid API key is available, try API fallback
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
                details = []
                if mg_err:
                    details.append(f"Mailgun error: {mg_err}")
                details.append(f"SMTP error: {repr(e)}")
                details.append(f"SendGrid error: {repr(se)}")
                return {"error": "; ".join(details)}
        # If no HTTP fallback used/available, return original SMTP error (and Mailgun error if present)
        if mg_err:
            return {"error": f"SMTP error: {repr(e)}; Mailgun error: {mg_err}"}
        return {"error": repr(e)}


def send_mailgun_email(to_email: str, subject: str, text: str | None = None, html: str | None = None) -> dict:
    """Send email via Mailgun HTTP API using MAILGUN_API_KEY and MAILGUN_DOMAIN.

    Backwards-compatible: if callers pass `text` only, pass as plain text. Callers can pass `html` too.
    Returns {'ok': True} or {'error': 'message'}
    """
    mg_key = os.getenv("MAILGUN_API_KEY")
    mg_domain = os.getenv("MAILGUN_DOMAIN")
    mail_from = os.getenv("MAIL_FROM") or os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")
    if not (mg_key and mg_domain and mail_from and to_email):
        return {"error": "Missing Mailgun configuration or recipient"}

    mg_url = f"https://api.mailgun.net/v3/{mg_domain}/messages"
    payload = {
        "from": f"The Turning Point <{mail_from}>",
        "to": to_email,
        "subject": subject,
    }
    if text:
        payload["text"] = text
    else:
        payload["text"] = ""
    if html:
        payload["html"] = html

    try:
        r = requests.post(mg_url, auth=("api", mg_key), data=payload, timeout=10)
        if r.status_code in (200, 202):
            return {"ok": True}
        return {"error": f"Mailgun error: {r.status_code} {r.text}"}
    except Exception as e:
        return {"error": repr(e)}


def send_email(to_email: str, subject: str, body: str) -> dict:
    """Send a plain-text email to `to_email` using SMTP credentials from env.

    Expects env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
    Returns {'ok': True} or {'error': 'message'}
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender_name = os.getenv("SENDER_NAME")
    sender_email = os.getenv("SENDER_EMAIL") or user

    if not (host and user and password and to_email):
        return {"error": "Missing SMTP configuration or recipient email"}

    msg = EmailMessage()
    msg["Subject"] = subject
    if sender_name:
        msg["From"] = f"{sender_name} <{sender_email}>"
    else:
        msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content(body)

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
        # Try Mailgun HTTP API if configured
        mg_key = os.getenv("MAILGUN_API_KEY")
        mg_domain = os.getenv("MAILGUN_DOMAIN")
        if mg_key and mg_domain:
            try:
                from_email = os.getenv("SENDER_EMAIL") or user
                sender_name = os.getenv("SENDER_NAME")
                mg_from = f"{sender_name} <{from_email}>" if sender_name else from_email
                mg_url = f"https://api.mailgun.net/v3/{mg_domain}/messages"
                data = {"from": mg_from, "to": to_email, "subject": subject, "text": body}
                r = requests.post(mg_url, auth=("api", mg_key), data=data, timeout=10)
                if r.status_code in (200, 202):
                    return {"ok": True}
                return {"error": f"Mailgun error: {r.status_code} {r.text}"}
            except Exception as me:
                mg_err = repr(me)
        else:
            mg_err = None

        # Try SendGrid API fallback
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
                details = []
                if mg_err:
                    details.append(f"Mailgun error: {mg_err}")
                details.append(f"SMTP error: {repr(e)}")
                details.append(f"SendGrid error: {repr(se)}")
                return {"error": "; ".join(details)}
        if mg_err:
            return {"error": f"SMTP error: {repr(e)}; Mailgun error: {mg_err}"}
        return {"error": repr(e)}
