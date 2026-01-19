import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import httpx


def init_session():
    defaults = {
        "authenticated": False,
        "user": None,
        "role": None,
        "email": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource
def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def restore_session_from_refresh(refresh_token: str) -> dict | None:
    """Exchange a refresh token for a new session via Supabase Auth endpoint.

    Returns the JSON response (access_token, refresh_token, user) on success,
    or None on failure.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=refresh_token"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(url, json={"refresh_token": refresh_token}, headers=headers, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None
