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

st.markdown("This page runs simple connectivity checks for your SMTP server and SendGrid API. It does not reveal secrets.")

smtp_host = os.getenv("SMTP_HOST")
smtp_port = os.getenv("SMTP_PORT") or "587"
sg_key = os.getenv("SENDGRID_API_KEY")
sender = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")

st.write("**Configured values (masked):**")
st.write(f"SMTP_HOST: {mask(smtp_host)}")
st.write(f"SMTP_PORT: {smtp_port}")
st.write(f"SENDER_EMAIL: {mask(sender)}")
st.write(f"SENDGRID_API_KEY: {mask(sg_key)}")

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

    # Test SendGrid API reachability
    try:
        # If API key present, do an authenticated request to get a clear status
        headers = {"Authorization": f"Bearer {sg_key}"} if sg_key else {}
    except Exception:
        headers = {}

    try:
        # simple GET to SendGrid root endpoint
        r = requests.get("https://api.sendgrid.com/v3/user/profile", headers=headers, timeout=8)
        results['sendgrid_status'] = f"HTTP {r.status_code}"
        if r.text:
            results['sendgrid_body'] = r.text[:500]
    except Exception as e:
        results['sendgrid_status'] = f"REQUEST_FAIL: {e}"

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
