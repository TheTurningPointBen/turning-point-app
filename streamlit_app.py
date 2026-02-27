import streamlit as st
from utils.ui import hide_sidebar
from utils.session import init_session
from utils.ui import safe_rerun

# Configure the app once (must be called only once) and before any other Streamlit calls
st.set_page_config(
    page_title="The Turning Point", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="🎈"
)

# ===== CUSTOM CSS FOR PROFESSIONAL STYLING =====
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    /* Global Styling */
    * {
        font-family: 'Poppins', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Logo Container */
    .logo-container {
        text-align: center;
        padding: 2rem 0;
        background: white;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 3rem;
    }
    
    .logo-container img {
        max-width: 450px;
        width: 90%;
        height: auto;
    }
    
    /* Main Title Styling */
    h1 {
        color: #dc143c;
        font-weight: 700;
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Subtitle */
    .stSubheader, h3 {
        color: #555;
        text-align: center;
        font-weight: 600;
        margin-bottom: 2rem;
    }
    
    /* Role Card Container */
    .role-cards-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Role Card Styling */
    .stButton > button {
        width: 100%;
        height: 200px;
        background: white;
        border: 3px solid #e0e0e0;
        border-radius: 20px;
        font-size: 1.5rem;
        font-weight: 600;
        color: #333;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #dc143c 0%, #a10000 100%);
        color: white;
        border-color: #dc143c;
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(220, 20, 60, 0.3);
    }
    
    .stButton > button:active {
        transform: translateY(-2px);
    }
    
    /* Button Icons - Make them larger */
    .stButton > button::before {
        font-size: 3rem;
        display: block;
        margin-bottom: 0.5rem;
    }
    
    /* Column spacing */
    [data-testid="column"] {
        padding: 1rem;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Remove extra padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* Tagline */
    .tagline {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        font-style: italic;
        margin-bottom: 3rem;
        padding: 1rem;
    }
    
    .tagline strong {
        color: #dc143c;
    }
    
    /* Decorative elements */
    .balloon-decoration {
        font-size: 2rem;
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    /* Role card custom styling */
    .role-card-parent {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .role-card-tutor {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    .role-card-admin {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    </style>
""", unsafe_allow_html=True)

# Ensure session state defaults exist for all pages
init_session()

# Detect simple recovery param and forward to password reset page
try:
    params = st.query_params or {}
    if "recovery" in params:
        try:
            st.session_state["recovery"] = params["recovery"]
        except Exception:
            pass
        try:
            st.switch_page("pages/password_reset.py")
            st.stop()
        except Exception:
            pass
except Exception:
    pass

# If the root URL includes a Supabase recovery token (?type=recovery&access_token=...)
# dispatch directly to the password_reset page so links that land on the homepage
# will still surface the password reset UI.
try:
    qp = {}
    try:
        qp = st.query_params or {}
    except Exception:
        try:
            qp = st.query_params or {}
        except Exception:
            qp = {}
    qp_type = (qp.get('type') or [None])[0]
    qp_token = (qp.get('access_token') or [None])[0]
    if qp_type == 'recovery' and qp_token:
        try:
            try:
                st.switch_page("pages/password_reset.py")
                st.stop()
            except Exception:
                pass

            import runpy, os
            base_dir = os.path.dirname(__file__)
            candidate = os.path.join(base_dir, 'pages', 'password_reset.py')
            if os.path.isfile(candidate):
                runpy.run_path(candidate, run_name='__main__')
                st.stop()
        except Exception:
            try:
                st.session_state['page'] = 'password_reset'
                st.experimental_rerun()
            except Exception:
                pass
except Exception:
    pass

# Ensure a default `page` query param exists for unauthenticated users
if not st.session_state.get("authenticated"):
    try:
        if not st.session_state.get('page'):
            st.session_state['page'] = 'homepage'
            try:
                st.experimental_rerun()
            except Exception:
                pass
    except Exception:
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

# Client-side redirect for recovery tokens
try:
    st.markdown(
        """
        <script>
        (function(){
            try{
                function scheduleRedirect(dest){
                    if(window.location.pathname !== '/password_reset'){
                        var tryRedirect = function(){ try{ window.location.replace(dest); }catch(e){} };
                        var iv = setInterval(tryRedirect, 150);
                        setTimeout(function(){ clearInterval(iv); }, 3000);
                    }
                }

                const params = new URLSearchParams(window.location.search || '');
                const t = params.get('type');
                const token = params.get('access_token');
                if(t === 'recovery' && token){
                    const dest = '/password_reset?type=recovery&access_token=' + encodeURIComponent(token);
                    scheduleRedirect(dest);
                    return;
                }

                if(window.location.hash){
                    const frag = window.location.hash.replace(/^#/, '');
                    const fparams = new URLSearchParams(frag);
                    const ft = fparams.get('type');
                    const ftoken = fparams.get('access_token');
                    if(ft === 'recovery' && ftoken){
                        const dest = '/password_reset?type=recovery&access_token=' + encodeURIComponent(ftoken);
                        scheduleRedirect(dest);
                        return;
                    }
                }
            }catch(e){}
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
except Exception:
    pass

# Compatibility shim for experimental_rerun
try:
    if not hasattr(st, 'experimental_rerun'):
        setattr(st, 'experimental_rerun', safe_rerun)
except Exception:
    pass

# Dispatcher early so root app doesn't also render the same page
import runpy
import os

def _dispatch_page_early():
    page = st.session_state.get('page')
    if not page:
        return

    base_dir = os.path.dirname(__file__)
    candidate = os.path.join(base_dir, 'pages', f"{page}.py")
    if not os.path.isfile(candidate):
        candidate = os.path.join(base_dir, 'pages_disabled', f"{page}.py")
        if not os.path.isfile(candidate):
            return

    try:
        # Avoid executing page modules in-process with `runpy.run_path` —
        # that registers Streamlit widgets twice and leads to duplicate
        # element key errors. Prefer `st.switch_page` when available so
        # the multipage loader handles the page, otherwise perform a
        # client-side redirect to the page path.
        try:
            st.switch_page(f"pages/{page}.py")
            st.stop()
        except Exception:
            # Client-side redirect to the multipage route (e.g. /password_reset)
            try:
                dest = f"/{page}"
                st.markdown(f"<script>window.location.href='{dest}';</script>", unsafe_allow_html=True)
                st.stop()
            except Exception:
                pass
    except Exception:
        pass

_dispatch_page_early()

# ===== LOGO HEADER =====
st.markdown("""
    <div class="logo-container">
        <img src="https://raw.githubusercontent.com/TheTurningPointBen/turning-point-app/main/logo.jpg" alt="The Turning Point Logo">
    </div>
""", unsafe_allow_html=True)

# ===== MAIN CONTENT =====
st.title("🎈 The Turning Point")
st.markdown("""
    <div class="tagline">
        <strong>Educational & Emotional Support for Children</strong><br>
        <span class="balloon-decoration">🎈</span> It's only up from HERE!
    </div>
""", unsafe_allow_html=True)

st.subheader("Select Your Portal")

# Hide Streamlit Pages list in sidebar
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

# ===== ROLE SELECTION CARDS =====
st.markdown('<div class="role-cards-container">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("👨‍👩‍👧 Parent Portal", key="parent_btn"):
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
    if st.button("🎓 Tutor Portal", key="tutor_btn"):
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
    if st.button("🔐 Admin Portal", key="admin_btn"):
        try:
            st.session_state['page'] = 'admin'
            st.session_state.role = 'admin'
            try:
                st.experimental_rerun()
            except Exception:
                pass
        except Exception:
            st.session_state.role = 'admin'

st.markdown('</div>', unsafe_allow_html=True)

# ===== FOOTER =====
st.markdown("""
    <div style="text-align: center; margin-top: 4rem; padding: 2rem; color: #999; font-size: 0.9rem;">
        <p>🎈 <strong>The Turning Point Pty Ltd</strong></p>
        <p>Educational & Emotional Support for Children | © 2024 All rights reserved.</p>
    </div>
""", unsafe_allow_html=True)

# Simple dispatcher
def _dispatch_page():
    page = st.session_state.get('page')
    if not page or page in ('home', 'landing'):
        return

    base_dir = os.path.dirname(__file__)
    candidate = os.path.join(base_dir, 'pages', f"{page}.py")
    if not os.path.isfile(candidate):
        candidate = os.path.join(base_dir, 'pages_disabled', f"{page}.py")
        if not os.path.isfile(candidate):
            st.error(f"Page not found: {page}")
            return

    try:
        try:
            st.switch_page(f"pages/{page}.py")
            st.stop()
        except Exception:
            dest = f"/{page}"
            st.markdown(f"<script>window.location.href='{dest}';</script>", unsafe_allow_html=True)
            st.stop()
    except Exception as e:
        st.error(f"Failed to load page '{page}': {e}")

_dispatch_page()
