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
    # Helper to send via SendGrid
    def _send_via_sendgrid(to_addr: str, subject_text: str, body_text: str) -> dict:
        sg_key = os.getenv("SENDGRID_API_KEY")
        if not sg_key:
            return {"error": "no-sendgrid-key"}
        from_email = os.getenv("SENDER_EMAIL") or user
        sender_name = os.getenv("SENDER_NAME")
        payload = {
            "personalizations": [{"to": [{"email": to_addr}]}],
            "from": {"email": from_email},
            "subject": subject_text,
            "content": [{"type": "text/plain", "value": body_text}],
        }
        if sender_name:
            payload["from"]["name"] = sender_name
        headers = {"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"}
        try:
            r = requests.post("https://api.sendgrid.com/v3/mail/send", data=json.dumps(payload), headers=headers, timeout=10)
            if r.status_code in (200, 202):
                return {"ok": True}
            return {"error": f"SendGrid error: {r.status_code} {r.text}"}
        import os
        import smtplib
        from email.message import EmailMessage
        import json
        import requests
        from typing import Optional, Dict


        def _send_via_sendgrid(to_addr: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
            """Send email using SendGrid HTTP API. Returns {'ok': True} or {'error': '...'}"""
            sg_key = os.getenv("SENDGRID_API_KEY")
            if not sg_key:
                return {"error": "no-sendgrid-key"}
            from_email = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_FROM")
            if not from_email:
                return {"error": "no-sender-email"}
            sender_name = os.getenv("SENDER_NAME")

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
            if sender_name:
                payload["from"]["name"] = sender_name

            headers = {"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"}
            try:
                r = requests.post("https://api.sendgrid.com/v3/mail/send", data=json.dumps(payload), headers=headers, timeout=10)
                if r.status_code in (200, 202):
                    return {"ok": True}
                return {"error": f"SendGrid error: {r.status_code} {r.text}"}
            except Exception as e:
                return {"error": f"SendGrid exception: {repr(e)}"}


        def _send_via_smtp(msg: EmailMessage) -> Dict:
            """Send EmailMessage via SMTP using env vars. Returns {'ok': True} or {'error': '...'}"""
            host = os.getenv("SMTP_HOST")
            port = int(os.getenv("SMTP_PORT", "587"))
            user = os.getenv("SMTP_USER")
            password = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS")

            if not (host and user and password):
                return {"error": "missing-smtp-config"}

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
                # Try implicit SSL port 465 as a fallback
                try:
                    with smtplib.SMTP_SSL(host, 465, timeout=30) as smtp:
                        smtp.login(user, password)
                        smtp.send_message(msg)
                    return {"ok": True}
                except Exception:
                    return {"error": f"SMTP exception: {repr(e)}"}


        def send_email(to_email: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
            """Send an email to `to_email`.

            Honors env `EMAIL_PROVIDER` if set to 'sendgrid' to prefer SendGrid first.
            Falls back between SMTP and SendGrid where possible.
            """
            provider = (os.getenv("EMAIL_PROVIDER") or "").lower()

            # If provider prefers sendgrid, try it first
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
                if sg_res.get("ok"):
                    return {"ok": True}

            # Build EmailMessage for SMTP
            sender_name = os.getenv("SENDER_NAME")
            sender_email = os.getenv("EMAIL_FROM") or os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")
            if not sender_email:
                return {"error": "no-sender-email"}

            msg = EmailMessage()
            msg["Subject"] = subject
            if sender_name:
                msg["From"] = f"{sender_name} <{sender_email}>"
            else:
                msg["From"] = sender_email
            msg["To"] = to_email
            msg.set_content(body or "")
            if html:
                try:
                    msg.add_alternative(html, subtype="html")
                except Exception:
                    pass

            smtp_res = _send_via_smtp(msg)
            if smtp_res.get("ok"):
                return {"ok": True}

            # If provider was explicitly sendgrid and SMTP failed, try SendGrid now
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
                if sg_res.get("ok"):
                    return {"ok": True}
                return {"error": f"SMTP failed; SendGrid: {sg_res.get('error')}"}

            # Otherwise, try SendGrid fallback
            sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
            if sg_res.get("ok"):
                return {"ok": True}

            return {"error": f"SMTP: {smtp_res.get('error')}; SendGrid: {sg_res.get('error')}"}


        def send_admin_email(subject: str, body: str, admin_email: Optional[str] = None) -> Dict:
            """Send a plain-text email to the admin address.

            Uses same provider preference rules as `send_email`.
            """
            provider = (os.getenv("EMAIL_PROVIDER") or "").lower()
            user = os.getenv("SMTP_USER")
            sender_name = os.getenv("SENDER_NAME")
            sender_email = os.getenv("EMAIL_FROM") or os.getenv("SENDER_EMAIL") or user
            admin = admin_email or os.getenv("ADMIN_EMAIL") or sender_email

            if not admin:
                return {"error": "no-admin-email"}

            # If provider prefers sendgrid, try it first
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(admin, subject, body)
                if sg_res.get("ok"):
                    return {"ok": True}

            # Build EmailMessage and try SMTP
            msg = EmailMessage()
            msg["Subject"] = subject
            if sender_name:
                msg["From"] = f"{sender_name} <{sender_email}>"
            else:
                msg["From"] = sender_email
            msg["To"] = admin
            msg.set_content(body or "")

            smtp_res = _send_via_smtp(msg)
            if smtp_res.get("ok"):
                return {"ok": True}

            # If provider preference was sendgrid, try it after SMTP
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(admin, subject, body)
                if sg_res.get("ok"):
                    return {"ok": True}
                return {"error": f"SMTP failed; SendGrid: {sg_res.get('error')}"}

            # Otherwise try SendGrid as fallback
            sg_res = _send_via_sendgrid(admin, subject, body)
            if sg_res.get("ok"):
                return {"ok": True}

            return {"error": f"SMTP: {smtp_res.get('error')}; SendGrid: {sg_res.get('error')}"}


        def send_mailgun_email(to_email: str, subject: str, text: Optional[str] = None, html: Optional[str] = None) -> Dict:
            """Compatibility wrapper: route old Mailgun calls to current send_email.

            Keeps older pages working that import `send_mailgun_email`.
            """
            body = text or ""
            try:
                return send_email(to_email, subject, body, html=html)
            except Exception as e:
                return {"error": repr(e)}
