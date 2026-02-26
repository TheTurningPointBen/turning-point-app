import os
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


def set_auth_user_password(user_id: str, new_password: str) -> dict:
    """Set a Supabase Auth user's password via Admin API using the service role key.

    Requires `SUPABASE_SERVICE_ROLE` env var. Returns {'ok': True} or {'error': msg}.
    """
    svc = os.getenv('SUPABASE_SERVICE_ROLE')
    if not svc:
        return {'error': 'SUPABASE_SERVICE_ROLE not configured'}
    if not SUPABASE_URL:
        return {'error': 'SUPABASE_URL not configured'}

    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        'apikey': svc,
        'Authorization': f'Bearer {svc}',
        'Content-Type': 'application/json'
    }
    body = {'password': new_password}
    try:
        resp = httpx.put(url, headers=headers, json=body, timeout=10.0)
        if resp.status_code in (200, 204):
            return {'ok': True}
        else:
            try:
                return {'error': resp.json()}
            except Exception:
                return {'error': f'Status {resp.status_code}: {resp.text}'}
    except Exception as e:
        return {'error': str(e)}


def get_supabase_service():
    """Return a Supabase client using the service role key from SUPABASE_SERVICE_ROLE.

    Raises RuntimeError if the env var is not set.
    """
    svc = os.getenv('SUPABASE_SERVICE_ROLE')
    if not svc:
        raise RuntimeError('SUPABASE_SERVICE_ROLE not configured')
    if not SUPABASE_URL:
        raise RuntimeError('SUPABASE_URL not configured')
    # Create a client using the service role
    return create_client(SUPABASE_URL, svc)


def generate_recovery_link(email: str) -> dict:
    """Generate a password recovery link via Supabase Admin API.

    Uses the Supabase project's Site URL (configured in Supabase) rather
    than sending an explicit `redirect_to`. Requires `SUPABASE_SERVICE_ROLE`.
    Returns {'ok': True, 'link': url} on success or {'error': msg} on failure.
    """
    svc = os.getenv('SUPABASE_SERVICE_ROLE')
    # If service role key isn't configured, fall back to the project's
    # public client and ask Supabase to send a recovery email using the
    # configured `redirect_to` so the token lands back at our app.
    if not svc:
        try:
            # Use the regular project client to request a password reset
            # email. This uses Supabase's SMTP/email provider configured
            # in the project and accepts a `redirect_to` parameter.
            site = os.getenv('SITE_URL') or os.getenv('APP_URL') or 'http://localhost:8501'
            redirect_to = site.rstrip('/') + '/password_reset'
            try:
                sup = get_supabase()
            except Exception:
                # If we cannot construct the client, return an informative error
                return {'error': 'Supabase client not configured (SUPABASE_URL/SUPABASE_KEY)'}

            try:
                res = sup.auth.reset_password_for_email(email, {"redirect_to": redirect_to})
            except Exception as e:
                try:
                    # Some client versions return a dict under `data`/`error`
                    return {'error': str(e)}
                except Exception:
                    return {'error': 'Failed to request password reset'}

            # Normalize result
            ok = False
            out = {}
            try:
                if getattr(res, 'get', None):
                    # dict-like
                    out.update(res)
                    if not out.get('error'):
                        ok = True
                else:
                    # object-like from newer clients
                    data = getattr(res, 'data', None)
                    error = getattr(res, 'error', None)
                    if data:
                        out['response'] = data
                    if not error:
                        ok = True
                    else:
                        out['error'] = error
            except Exception:
                out = {'response': str(res)}

            if ok:
                out['ok'] = True
            return out
        except Exception as e:
            return {'error': str(e)}
    if not SUPABASE_URL:
        return {'error': 'SUPABASE_URL not configured'}

    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/generate_link"
    headers = {
        'apikey': svc,
        'Authorization': f'Bearer {svc}',
        'Content-Type': 'application/json'
    }
    # Do NOT send an explicit `redirect_to` — let Supabase use the
    # project's configured Site URL. This avoids mismatches and keeps
    # token delivery consistent across environments.
    body = {'type': 'recovery', 'email': email}
    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=10.0)
        if resp.status_code in (200, 201):
            try:
                j = resp.json()
            except Exception:
                j = None

            # Attempt to extract any returned link-like fields
            link = None
            if isinstance(j, dict):
                link = j.get('link') or j.get('url') or j.get('action_link') or j.get('generated_link')

            text = resp.text or ''
            # If we didn't find a link in JSON, attempt to find tokens or links in the raw text
            if not link:
                import re
                m = re.search(r"(https?://[^\s'\"]+)", text)
                if m:
                    link = m.group(1)

            # Try to extract an access_token from either JSON values or the response text
            token = None
            try:
                import re
                if isinstance(j, dict):
                    # search all string values
                    for v in j.values():
                        if isinstance(v, str):
                            mm = re.search(r"access_token=([A-Za-z0-9_\-\.]+)", v)
                            if mm:
                                token = mm.group(1)
                                break
                if not token:
                    mm = re.search(r"access_token=([A-Za-z0-9_\-\.]+)", text)
                    if mm:
                        token = mm.group(1)
            except Exception:
                token = None

            site = os.getenv('SITE_URL') or os.getenv('APP_URL') or 'http://localhost:8501'
            direct = None
            if token:
                direct = site.rstrip('/') + f"/password_reset?type=recovery&access_token={token}"

            out = {'ok': True}
            if link:
                out['link'] = link
            if direct:
                out['direct_link'] = direct
            if j:
                out['response'] = j
            else:
                out['text'] = text
            return out
        else:
            try:
                return {'error': resp.json()}
            except Exception:
                return {'error': f'Status {resp.status_code}: {resp.text}'}
    except Exception as e:
        return {'error': str(e)}
