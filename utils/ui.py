import os
import streamlit as st
from datetime import datetime, timedelta


INACTIVITY_TIMEOUT_MINUTES = int(os.getenv("INACTIVITY_TIMEOUT_MINUTES", "15"))


def _clear_auth_session_and_redirect_home(reason: str | None = None):
    """Clear auth/session keys and return the user to the homepage."""
    keep_keys = {"_is_running"}
    for k in list(st.session_state.keys()):
        if k in keep_keys:
            continue
        try:
            del st.session_state[k]
        except Exception:
            pass

    st.session_state["page"] = "homepage"
    if reason:
        st.session_state["flash_warning"] = reason

    try:
        st.rerun()
        return
    except Exception:
        pass
    try:
        st.experimental_rerun()
        return
    except Exception:
        pass
    try:
        st.markdown("<script>window.location.href='/'</script>", unsafe_allow_html=True)
    except Exception:
        pass
    try:
        st.stop()
    except Exception:
        pass


def enforce_inactivity_timeout(timeout_minutes: int = INACTIVITY_TIMEOUT_MINUTES):
    """Auto-logout authenticated users after a period of inactivity."""
    try:
        if st.session_state.get("flash_warning"):
            st.warning(st.session_state.pop("flash_warning"))
    except Exception:
        pass

    is_auth = bool(st.session_state.get("authenticated"))
    role = st.session_state.get("role")
    protected_roles = {"parent", "tutor", "admin"}

    if not is_auth or role not in protected_roles:
        st.session_state.pop("_last_activity_at", None)
        return

    now = datetime.utcnow()
    last_raw = st.session_state.get("_last_activity_at")
    if last_raw:
        try:
            last_dt = datetime.fromisoformat(last_raw)
            if now - last_dt > timedelta(minutes=timeout_minutes):
                _clear_auth_session_and_redirect_home(
                    f"You were logged out after {timeout_minutes} minutes of inactivity."
                )
                return
        except Exception:
            pass

    st.session_state["_last_activity_at"] = now.isoformat()


def top_header(image_path="assets/topright.png", height=88):
    """Render a compact top-right header image across pages.

    This helper intentionally does not modify or hide Streamlit's
    sidebar or Pages list. It only renders a small header image (or
    placeholder) so pages can include a consistent brand element.
    """
    try:
        image_css = f"""
<style>
.tp-topright {{
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 9999;
    background: rgba(255,255,255,0.0);
    padding: 4px;
    border-radius: 6px;
}}
.tp-topright img {{
    height: {height}px;
    object-fit: contain;
    display:block;
}}
</style>
"""

        if os.path.exists(image_path):
            img_tag = f'<div class="tp-topright"><img src="/{image_path}" alt="Turning Point"></div>'
            st.markdown(image_css + img_tag, unsafe_allow_html=True)
        else:
            placeholder = (
                image_css
                + '<div class="tp-topright"><div style="height: '
                + str(height)
                + 'px; padding:6px;border:1px solid #eee;border-radius:6px;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.05);'>
                + "<div style='text-align:center;font-size:12px;color:#444;'>Add header image<br><strong>assets/topright.png</strong></div></div></div>"
            )
            st.markdown(placeholder, unsafe_allow_html=True)
    except Exception:
        # Fail silently so pages still load in non-Streamlit contexts
        pass


def hide_sidebar():
    """Hide the Streamlit sidebar and collapse it by default.

    Use this helper at the top of every page to ensure the Pages list
    and sidebar toggle are not visible to non-admin users.
    """
    # Do NOT call st.set_page_config() here — it must only be called once
    # from the main entrypoint (streamlit_app.py). Calling it from every
    # page causes a Streamlit runtime error during deploy.

    st.markdown(
        """
        <style>
        /* Hide sidebar */
        section[data-testid="stSidebar"] {
            display: none !important;
        }

        /* Hide sidebar toggle (hamburger) */
        button[data-testid="collapsedControl"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Apply global inactivity handling for authenticated portal users.
    enforce_inactivity_timeout()


def safe_rerun():
    """Try to rerun the Streamlit app in a compatible way across versions.

    This will attempt `st.experimental_rerun()` if available, otherwise
    fall back to a client-side reload and stop the script.
    """
    try:
        # Preferred method (may be missing on some Streamlit builds)
        getattr(st, 'experimental_rerun')()
        return
    except Exception:
        pass

    try:
        # Try to nudge Streamlit to update query params and rerun
        try:
            st.query_params
        except Exception:
            pass
        # Client-side reload fallback
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
    except Exception:
        try:
            st.stop()
        except Exception:
            pass
