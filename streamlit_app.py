import streamlit as st
from utils.ui import hide_sidebar
from utils.session import init_session

# Configure the app once (must be called only once) and before any other Streamlit calls
st.set_page_config(page_title="The Turning Point", layout="wide", initial_sidebar_state="collapsed")

# Ensure session state defaults exist for all pages
init_session()
# Ensure a default `page` query param exists for unauthenticated users so
# Streamlit's multipage auto-loading doesn't pick a sidebar page on refresh.
if not st.session_state.get("authenticated"):
    try:
        if "page" not in st.query_params:
            st.query_params["page"] = "home"
    except Exception:
        # Fallback: client-side replace URL and hide sidebar
        st.markdown(
            """
            <script>
            (function(){
                try{
                    if(window.location.pathname !== '/'){
                        history.replaceState(null, '', '/');
                    }
                    setTimeout(()=>{
                        const aside = document.querySelector('aside');
                        if(aside) aside.style.display = 'none';
                    }, 50);
                }catch(e){}
            })();
            </script>
            """,
            unsafe_allow_html=True,
        )

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
            st.session_state['page'] = 'parent'
            st.session_state.role = 'parent'
            try:
                st.experimental_rerun()
            except Exception:
                pass
        except Exception:
            st.session_state.role = 'parent'
with col2:
    if st.button("🎓 Tutor"):
        try:
            st.session_state['page'] = 'tutor_login'
            st.session_state.role = 'tutor'
            try:
                st.experimental_rerun()
            except Exception:
                pass
        except Exception:
            st.session_state.role = 'tutor'
with col3:
    if st.button("🔑 Admin"):
        try:
            st.session_state['page'] = 'admin'
            st.session_state.role = 'admin'
            try:
                st.experimental_rerun()
            except Exception:
                pass
        except Exception:
            st.session_state.role = 'admin'


# Simple dispatcher: if a page key is set in session, execute the matching
# module under `pages_disabled/` so navigation works without Streamlit Pages.
import runpy
import os

def _dispatch_page():
    page = st.session_state.get('page')
    if not page or page in ('home', 'landing'):
        return

    base_dir = os.path.dirname(__file__)
    # Prefer the active `pages/` directory (Streamlit multipage), fallback to
    # `pages_disabled/` if present (older copy). This allows toggling without
    # breaking the dispatcher.
    candidate = os.path.join(base_dir, 'pages', f"{page}.py")
    if not os.path.isfile(candidate):
        candidate = os.path.join(base_dir, 'pages_disabled', f"{page}.py")
        if not os.path.isfile(candidate):
            st.error(f"Page not found: {page}")
            return

    try:
        runpy.run_path(candidate, run_name="__main__")
        st.stop()
    except Exception as e:
        st.error(f"Failed to load page '{page}': {e}")


_dispatch_page()
