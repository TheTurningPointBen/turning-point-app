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


def delete_auth_user(user_id: str) -> dict:
    """Delete a Supabase Auth user via the Admin API using the service role key.

    Requires environment variable `SUPABASE_SERVICE_ROLE` to be set.
    Returns {'ok': True} on success or {'error': 'msg'} on failure.
    """
    svc = os.getenv('SUPABASE_SERVICE_ROLE')
    if not svc:
        return {'error': 'SUPABASE_SERVICE_ROLE not configured'}
    if not SUPABASE_URL:
        return {'error': 'SUPABASE_URL not configured'}

    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        'apikey': svc,
        'Authorization': f'Bearer {svc}'
    }
    try:
        resp = httpx.delete(url, headers=headers, timeout=10.0)
        if resp.status_code in (200, 204):
            return {'ok': True}
        else:
            try:
                return {'error': resp.json()}
            except Exception:
                return {'error': f'Status {resp.status_code}: {resp.text}'}
    except Exception as e:
        return {'error': str(e)}
