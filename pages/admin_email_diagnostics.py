import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
from utils.session import restore_session_from_refresh
import socket
import os
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

st.markdown("This page runs simple connectivity checks for your SMTP server and Mailblaze HTTP API. It does not reveal secrets.")

smtp_host = os.getenv("SMTP_HOST")
smtp_port = os.getenv("SMTP_PORT") or "587"
mb_key = (
    os.getenv("MAILBLAZE_API_KEY")
    or os.getenv("MAILBLAZE_KEY")
    or os.getenv("mailblaze_api_key")
    or os.getenv("MAILBLAZE_APIKEY")
)
mb_base = os.getenv("MAILBLAZE_BASE") or os.getenv("MAILBLAZE_BASE_URL") or os.getenv('mailblaze_http') or "https://control.mailblaze.com/api"
sender = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")

st.write("**Configured values (masked):**")
st.write(f"SMTP_HOST: {mask(smtp_host)}")
st.write(f"SMTP_PORT: {smtp_port}")
st.write(f"SENDER_EMAIL: {mask(sender)}")
st.write(f"MAILBLAZE_API_KEY: {mask(mb_key)}")
st.write(f"MAILBLAZE_BASE: {mask(mb_base)}")

if st.button("Run connectivity tests"):
    results = {}
    # DNS resolution
    try:
        results['smtp_dns'] = socket.gethostbyname(smtp_host) if smtp_host else "missing"
    except Exception as e:
        results['smtp_dns'] = f"DNS error: {e}"

    # Socket connect to SMTP
    try:
        s = socket.socket()
        s.settimeout(6)
        s.connect((smtp_host, int(smtp_port)))
        s.close()
        results['smtp_connect'] = "OK"
    except Exception as e:
        results['smtp_connect'] = f"CONNECT_FAIL: {e}"

    # Test Mailblaze API reachability
    try:
        headers = {"Authorization": f"Bearer {mb_key}" } if mb_key else {}
    except Exception:
        headers = {}

    try:
        # try base URL and a couple common endpoints for debugging
        mb_results = []
        for ep in [mb_base, f"{mb_base}/v1/user", f"{mb_base}/v1/profile"]:
            try:
                r = requests.get(ep, headers=headers, timeout=8)
                mb_results.append((ep, r.status_code, (r.text or '')[:500]))
            except Exception as e:
                mb_results.append((ep, 'err', repr(e)))
        results['mailblaze'] = mb_results
    except Exception as e:
        results['mailblaze'] = f"REQUEST_FAIL: {e}"

    st.json(results)

    # Optionally attempt a test send (will actually send email) — only show if admin confirms
    if st.checkbox("Attempt to send a test email to my sender address (will deliver)"):
        test_to = sender
        if not test_to:
            st.error("No sender/recipient configured to receive test email.")
        else:
            from utils.email import send_admin_email
            res = send_admin_email("Test email from diagnostics", "This is a connectivity test.", admin_email=test_to)
            st.write(res)
