import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
from utils.session import restore_session_from_refresh
import socket
import os
import base64
import requests

try:
    st.set_page_config(page_title="Email Diagnostics")
except Exception:
    pass

st.title("Email Diagnostics")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

def mask(s):
    if not s:
        return "(missing)"
    if len(s) < 8:
        return "****"
    return s[:4] + "..." + s[-4:]

st.markdown("This page runs simple connectivity checks for your Mailblaze HTTP API and can send a test email. It does not reveal secrets.")

mb_key = (
    os.getenv("MAILBLAZE_API_KEY")
    or os.getenv("MAILBLAZE_KEY")
    or os.getenv("mailblaze_api_key")
    or os.getenv("MAILBLAZE_APIKEY")
)
mb_base = os.getenv("MAILBLAZE_BASE") or os.getenv("MAILBLAZE_BASE_URL") or os.getenv('mailblaze_http') or "https://control.mailblaze.com/api"
sender = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER")

st.write("**Configured values (masked):**)"
st.write(f"MAILBLAZE_API_KEY: {mask(mb_key)}")
st.write(f"MAILBLAZE_BASE: {mask(mb_base)}")
st.write(f"SENDER_EMAIL: {mask(sender)}")

# Show additional sender env variants and what the email helper resolves
try:
    from utils.email import _get_sender
    resolved = _get_sender()
except Exception:
    resolved = None
st.write(f"sender_email (env): {mask(os.getenv('sender_email'))}")
st.write(f"email_from (env): {mask(os.getenv('email_from'))}")
st.write(f"Resolved sender from helper: {mask(resolved)}")

if st.button("Check Mailblaze connectivity"):
    if not mb_base:
        st.error('Missing Mailblaze base URL (MAILBLAZE_BASE or mailblaze_http)')
    else:
        st.info(f'Attempting HTTPS GET to {mb_base} (5s timeout)')
        try:
            headers = {"Authorization": f"Bearer {mb_key}"} if mb_key else {}
            r = requests.get(mb_base, headers=headers, timeout=5)
            st.write(f'Status: {r.status_code}')
            if r.status_code < 400:
                st.success('Connectivity to Mailblaze base URL succeeded')
            else:
                st.error(f'Connectivity test returned status {r.status_code}')
        except Exception as e:
            st.error(f'Connectivity check failed: {e}')

# Mailblaze send test
try:
    default_from = sender
    mb_recipient = st.text_input('Mailblaze test recipient', value=default_from, key='diag_mb_test_recipient')
    mb_subject = st.text_input('Mailblaze test subject', value='Turning Point — Mailblaze test', key='diag_mb_test_subject')
    mb_body = st.text_area('Mailblaze test body (plain text)', value='This is a Mailblaze test email from Turning Point Admin.', key='diag_mb_test_body')
    if st.button('Send test via Mailblaze', key='diag_mb_send'):
        if not mb_key:
            st.error('MAILBLAZE_API_KEY (or mailblaze_api_key) is not set in environment')
        elif not default_from:
            st.error('SENDER_EMAIL or EMAIL_FROM is not configured')
        else:
            # Build transactional-style payload: base64-encode HTML/plain body
            try:
                encoded_body = base64.b64encode(mb_body.encode("utf-8")).decode("utf-8")
            except Exception:
                encoded_body = mb_body

            payload = {
                "to_email": mb_recipient,
                "to_name": None,
                "from_email": default_from,
                "from_name": os.getenv("MAILBLAZE_FROM_NAME") or os.getenv("EMAIL_FROM_NAME") or None,
                "subject": mb_subject,
                "body": encoded_body,
                "plain_text": encoded_body,
            }

            headers = {"authorization": mb_key, "Content-Type": "application/x-www-form-urlencoded"}
            base = mb_base
            endpoints = [f"{base.rstrip('/')}/transactional"]
            results = []
            for ep in endpoints:
                try:
                    r = requests.post(ep, data=payload, headers=headers, timeout=10)
                    results.append((ep, r.status_code, r.text))
                    if r.status_code in (200, 201, 202):
                        st.success(f'Mailblaze test send accepted via {ep}')
                        break
                except Exception as e:
                    results.append((ep, 'err', repr(e)))
            st.write('Results:')
            for ep, status, body in results:
                try:
                    st.text(f'{ep} → {status} — {body}')
                except Exception:
                    st.write(f'{ep} → {status}')
except Exception:
    pass
