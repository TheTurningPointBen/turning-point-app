import os
import streamlit as st


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
            st.experimental_set_query_params()
        except Exception:
            pass
        # Client-side reload fallback
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
    except Exception:
        try:
            st.stop()
        except Exception:
            pass
