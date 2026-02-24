import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()

try:
    st.set_page_config(page_title="Homepage")
except Exception:
    pass

st.title("Homepage")
st.markdown("Welcome to The Turning Point — choose a portal below.")

# If a Supabase recovery link landed here, show a prominent link to the
# password reset page so users can continue the flow.
# Client-side fragment -> query string converter

# Place this before any st.query_params usage so the page will reload with
# query params that Streamlit can read server-side.
try:
        st.markdown(
                """
                <script>
                (function() {
                    try {
                        const hash = window.location.hash || "";
                        if (!hash) return;
                        // Prevent repeated processing / infinite reload
                        if (window.location.search.includes("from_fragment=1")) return;
                        const params = new URLSearchParams(hash.slice(1));
                        const type = params.get("type");
                        const access_token = params.get("access_token") || params.get("token") || params.get("token_hash");
                            if (type === "recovery" && access_token) {
                                // Merge existing query params with values from fragment and
                                // include a target marker so server-side logic can prefer the
                                // in-app password reset flow without changing path.
                                const q = new URLSearchParams(window.location.search);
                                q.set("type", type);
                                q.set("access_token", access_token);
                                q.set("from_fragment", "1");
                                q.set("target", "password_reset");
                                const newUrl = window.location.origin + window.location.pathname + "?" + q.toString();
                                console.log('TP: merging fragment into query', {newUrl});
                                // Add a tiny DOM marker so we can confirm execution visually
                                try { document.documentElement.setAttribute('data-tp-fragment','1'); } catch(e){}
                                // Replace location so navigation history isn't polluted with the fragment URL
                                window.location.replace(newUrl);
                        }
                    } catch (e) {
                        console.error(e);
                    }
                })();
                </script>
                """,
                unsafe_allow_html=True,
        )
except Exception:
        # If injection fails, do not block page rendering
        pass
try:
    qp = st.query_params or {}
except Exception:
    qp = {}
qp_type = (qp.get('type') or [None])[0]
qp_token = (qp.get('access_token') or [None])[0]
qp_from = (qp.get('from_fragment') or [None])[0]
qp_target = (qp.get('target') or [None])[0]

# If this looks like a fragment-originated recovery link (from_fragment=1)
# and it targets the in-app password reset, clear query params and dispatch
# to the password reset UI using Streamlit's multipage switch when
# available. Otherwise fall back to the previous behavior.
if qp_type == 'recovery' and qp_token:
    if qp_from == '1' and qp_target == 'password_reset':
        try:
            try:
                st.experimental_set_query_params()
            except Exception:
                pass
            try:
                st.switch_page("pages/password_reset.py")
                st.stop()
            except Exception:
                # If switch_page is not available, keep inline flow below
                pass
        except Exception:
            pass
    else:
        # Non-fragment or older recovery links: keep previous behavior
        try:
            st.switch_page("pages/password_reset.py")
            st.stop()
        except Exception:
            st.error('It looks like you followed a password recovery link. Click the button below to open the password reset form.')
            try:
                dest = f"/password_reset?type=recovery&access_token={qp_token}"
                if st.button('Open password reset'):
                    st.markdown(f"<script>window.location.href='{dest}';</script>", unsafe_allow_html=True)
            except Exception:
                st.markdown(f"[Open password reset]({dest})")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("👤 Parent", key="homepage_parent"):
        try:
            st.switch_page("pages/parent.py")
        except Exception:
            st.session_state['page'] = 'parent'
            try:
                st.experimental_rerun()
            except Exception:
                pass

with col2:
    if st.button("🎓 Tutor", key="homepage_tutor"):
        try:
            st.switch_page("pages/tutor_login.py")
        except Exception:
            st.session_state['page'] = 'tutor_login'
            try:
                st.experimental_rerun()
            except Exception:
                pass

with col3:
    if st.button("🔑 Admin", key="homepage_admin"):
        try:
            st.switch_page("pages/admin.py")
        except Exception:
            st.session_state['page'] = 'admin'
            try:
                st.experimental_rerun()
            except Exception:
                pass
