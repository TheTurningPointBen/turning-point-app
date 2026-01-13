import streamlit as st

st.set_page_config(page_title="The Turning Point", layout="centered")

# Custom CSS for clean UI
st.markdown("""
    <style>
    .role-card { text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 10px; cursor: pointer; }
    .role-card:hover { background-color: #f0f2f6; }
    </style>
""", unsafe_allow_html=True)

st.title("The Turning Point Pty Ltd")
st.subheader("Select your portal")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("👤 Parent"):
        try:
            st.switch_page("pages/parent.py")
        except Exception:
            st.session_state.role = 'parent'
with col2:
    if st.button("🎓 Tutor"):
        try:
            st.switch_page("pages/tutor_login.py")
        except Exception:
            st.session_state.role = 'tutor'
with col3:
    if st.button("🔑 Admin"):
        try:
            st.switch_page("pages/admin.py")
        except Exception:
            st.session_state.role = 'admin'
