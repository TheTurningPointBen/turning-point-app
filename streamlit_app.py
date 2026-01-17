import streamlit as st
from utils.ui import hide_sidebar
from utils.session import init_session

# Ensure session state defaults exist for all pages
init_session()

# Configure the app once (must be called only once) then inject CSS
st.set_page_config(page_title="The Turning Point", layout="wide", initial_sidebar_state="collapsed")
hide_sidebar()

# Custom CSS for clean UI
st.markdown("""
    <style>
    .role-card { text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 10px; cursor: pointer; }
    .role-card:hover { background-color: #f0f2f6; }
    </style>
""", unsafe_allow_html=True)

st.title("The Turning Point Pty Ltd")
st.subheader("Select your portal")

# Hide Streamlit Pages list in the sidebar for a cleaner landing page
st.markdown(
    """
    <script>
    (function(){
        const hide = ()=>{
            try{
                const divs = Array.from(document.querySelectorAll('div'));
                for(const d of divs){
                    if(d.innerText && (d.innerText.trim().startsWith('Pages') || d.innerText.trim().startsWith('Page'))){
                        let node = d;
                        while(node && node.tagName !== 'ASIDE') node = node.parentElement;
                        if(node) node.remove(); else d.remove();
                        break;
                    }
                }
            }catch(e){}
        };
        setTimeout(hide, 200);
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

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
