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
try:
    qp = st.query_params or {}
except Exception:
    qp = {}
qp_type = (qp.get('type') or [None])[0]
qp_token = (qp.get('access_token') or [None])[0]
if qp_type == 'recovery' and qp_token:
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
