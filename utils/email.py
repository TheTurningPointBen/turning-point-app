import os
import smtplib
from email.message import EmailMessage
import json
import requests
from typing import Optional, Dict


def _send_via_sendgrid(to_addr: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
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
        or "https://control.mailblaze.com/api"
    )
    sender = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_FROM")
    if not sender:
        return {"error": "no-sender-email"}

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
    return {"error": f"Mailblaze error: {last_err}"}


def _send_via_smtp(msg: EmailMessage) -> Dict:
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
        try:
            with smtplib.SMTP_SSL(host, 465, timeout=30) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
            return {"ok": True}
        except Exception:
            return {"error": f"SMTP exception: {repr(e)}"}


def send_email(to_email: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
    provider = (os.getenv("EMAIL_PROVIDER") or "").lower()

    # If Mailblaze configured, prefer it regardless of EMAIL_PROVIDER
    mb_key_present = bool(
        os.getenv("MAILBLAZE_API_KEY") or os.getenv("MAILBLAZE_KEY") or os.getenv("mailblaze_api_key")
    )
    if mb_key_present and provider != "sendgrid":
        mb_try = _send_via_mailblaze(to_email, subject, body, html=html)
        if mb_try.get("ok"):
            return {"ok": True}

    # Honor explicit provider preference
    if provider == "sendgrid":
        sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
        if sg_res.get("ok"):
            return {"ok": True}
    elif provider == "mailblaze":
        mb_res = _send_via_mailblaze(to_email, subject, body, html=html)
        if mb_res.get("ok"):
            return {"ok": True}

    # Build EmailMessage for SMTP if possible
    sender_name = os.getenv("SENDER_NAME")
    sender_email = os.getenv("EMAIL_FROM") or os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")
    if not sender_email:
        # No sender; if Mailblaze available we already tried earlier. Return useful error.
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

    # If SMTP failed, try SendGrid then Mailblaze as fallbacks
    sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
    if sg_res.get("ok"):
        return {"ok": True}
    mb_res = _send_via_mailblaze(to_email, subject, body, html=html)
    if mb_res.get("ok"):
        return {"ok": True}

    return {"error": f"SMTP: {smtp_res.get('error')}; SendGrid: {sg_res.get('error')}; Mailblaze: {mb_res.get('error')}"}


def send_admin_email(subject: str, body: str, admin_email: Optional[str] = None) -> Dict:
    provider = (os.getenv("EMAIL_PROVIDER") or "").lower()
    user = os.getenv("SMTP_USER")
    sender_name = os.getenv("SENDER_NAME")
    sender_email = os.getenv("EMAIL_FROM") or os.getenv("SENDER_EMAIL") or user
    admin = admin_email or os.getenv("ADMIN_EMAIL") or sender_email

    if not admin:
        return {"error": "no-admin-email"}

    mb_key_present = bool(
        os.getenv("MAILBLAZE_API_KEY") or os.getenv("MAILBLAZE_KEY") or os.getenv("mailblaze_api_key")
    )
    if mb_key_present and provider != "sendgrid":
        mb_try = _send_via_mailblaze(admin, subject, body)
        if mb_try.get("ok"):
            return {"ok": True}

    if provider == "sendgrid":
        sg_res = _send_via_sendgrid(admin, subject, body)
        if sg_res.get("ok"):
            return {"ok": True}
    elif provider == "mailblaze":
        mb_res = _send_via_mailblaze(admin, subject, body)
        if mb_res.get("ok"):
            return {"ok": True}

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

    sg_res = _send_via_sendgrid(admin, subject, body)
    if sg_res.get("ok"):
        return {"ok": True}
    mb_res = _send_via_mailblaze(admin, subject, body)
    if mb_res.get("ok"):
        return {"ok": True}

    return {"error": f"SMTP: {smtp_res.get('error')}; SendGrid: {sg_res.get('error')}; Mailblaze: {mb_res.get('error')}"}


def send_mailgun_email(to_email: str, subject: str, text: Optional[str] = None, html: Optional[str] = None) -> Dict:
    body = text or ""
    try:
        return send_email(to_email, subject, body, html=html)
    except Exception as e:
        return {"error": repr(e)}
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


        def _send_via_mailblaze(to_addr: str, subject: str, body: str, html: Optional[str] = None) -> Dict:
            """Send via Mailblaze HTTP API. Base URL configurable by MAILBLAZE_BASE (defaults to control.mailblaze.com/api).
            Returns {'ok': True} or {'error': '...'} and exposes provider response for debugging.
            """
            mb_key = (
                os.getenv("MAILBLAZE_API_KEY")
                or os.getenv("MAILBLAZE_KEY")
                or os.getenv("MAILBLAZE_APIKEY")
                or os.getenv("mailblaze_api_key")
                or os.getenv("MAILBLAZE_APIKEY")
            )
            if not mb_key:
                return {"error": "no-mailblaze-key"}
            base = (
                os.getenv("MAILBLAZE_BASE")
                or os.getenv("MAILBLAZE_BASE_URL")
                or os.getenv("MAILBLAZE_BASEURL")
                or os.getenv("mailblaze_http")
                or os.getenv("MAILBLAZE_HTTP")
                or "https://control.mailblaze.com/api"
            )
            sender = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_FROM")
            if not sender:
                return {"error": "no-sender-email"}

            payload = {
                "personalizations": [{"to": [{"email": to_addr}]}],
                "from": {"email": sender},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body or ""}],
            }
            if html:
                payload["content"].append({"type": "text/html", "value": html})

            headers = {"Authorization": f"Bearer {mb_key}", "Content-Type": "application/json"}
            # Try common endpoint path; Mailblaze may vary — admin UI will show response for debugging
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
            return {"error": f"Mailblaze error: {last_err}"}


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

            # If provider prefers sendgrid or mailblaze, try preferred provider first
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
                if sg_res.get("ok"):
                    return {"ok": True}
            elif provider == "mailblaze":
                mb_res = _send_via_mailblaze(to_email, subject, body, html=html)
                if mb_res.get("ok"):
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

            # If provider was explicitly sendgrid or mailblaze and SMTP failed, try them now
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
                if sg_res.get("ok"):
                    return {"ok": True}
                return {"error": f"SMTP failed; SendGrid: {sg_res.get('error')}"}
            if provider == "mailblaze":
                mb_res = _send_via_mailblaze(to_email, subject, body, html=html)
                if mb_res.get("ok"):
                    return {"ok": True}
                return {"error": f"SMTP failed; Mailblaze: {mb_res.get('error')}"}

            # Otherwise, try SendGrid then Mailblaze as fallbacks
            sg_res = _send_via_sendgrid(to_email, subject, body, html=html)
            if sg_res.get("ok"):
                return {"ok": True}
            mb_res = _send_via_mailblaze(to_email, subject, body, html=html)
            if mb_res.get("ok"):
                return {"ok": True}

            return {"error": f"SMTP: {smtp_res.get('error')}; SendGrid: {sg_res.get('error')}; Mailblaze: {mb_res.get('error')}"}


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

            # If provider prefers sendgrid or mailblaze, try preferred provider first
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(admin, subject, body)
                if sg_res.get("ok"):
                    return {"ok": True}
            elif provider == "mailblaze":
                mb_res = _send_via_mailblaze(admin, subject, body)
                if mb_res.get("ok"):
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

            # If provider preference was sendgrid or mailblaze, try them after SMTP
            if provider == "sendgrid":
                sg_res = _send_via_sendgrid(admin, subject, body)
                if sg_res.get("ok"):
                    return {"ok": True}
                return {"error": f"SMTP failed; SendGrid: {sg_res.get('error')}"}
            if provider == "mailblaze":
                mb_res = _send_via_mailblaze(admin, subject, body)
                if mb_res.get("ok"):
                    return {"ok": True}
                return {"error": f"SMTP failed; Mailblaze: {mb_res.get('error')}"}

            # Otherwise try SendGrid then Mailblaze as fallbacks
            sg_res = _send_via_sendgrid(admin, subject, body)
            if sg_res.get("ok"):
                return {"ok": True}
            mb_res = _send_via_mailblaze(admin, subject, body)
            if mb_res.get("ok"):
                return {"ok": True}

            return {"error": f"SMTP: {smtp_res.get('error')}; SendGrid: {sg_res.get('error')}; Mailblaze: {mb_res.get('error')}"}


        def send_mailgun_email(to_email: str, subject: str, text: Optional[str] = None, html: Optional[str] = None) -> Dict:
            """Compatibility wrapper: route old Mailgun calls to current send_email.

            Keeps older pages working that import `send_mailgun_email`.
            """
            body = text or ""
            try:
                return send_email(to_email, subject, body, html=html)
            except Exception as e:
                return {"error": repr(e)}
