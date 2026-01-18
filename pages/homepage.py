import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()

try:
    st.set_page_config(page_title="Homepage")
except Exception:
    pass

st.title("Homepage")
st.markdown("Welcome to The Turning Point — choose a portal below.")

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
