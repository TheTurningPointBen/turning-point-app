import os
import smtplib
from email.message import EmailMessage

def send_admin_email(subject: str, body: str, admin_email: str | None = None) -> dict:
    """Send a plain-text email to the admin using SMTP credentials from env.

    Expects the following env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ADMIN_EMAIL
    Returns dict with either {'ok': True} or {'error': 'message'}
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    admin = admin_email or os.getenv("ADMIN_EMAIL")
    sender_name = os.getenv("SENDER_NAME")
    sender_email = os.getenv("SENDER_EMAIL") or user

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
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            try:
                smtp.starttls()
            except Exception:
                pass
            smtp.login(user, password)
            smtp.send_message(msg)
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}


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
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            try:
                smtp.starttls()
            except Exception:
                pass
            smtp.login(user, password)
            smtp.send_message(msg)
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}
