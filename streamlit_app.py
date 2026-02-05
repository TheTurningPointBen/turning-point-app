import streamlit as st
from utils.ui import hide_sidebar
from utils.session import init_session
from utils.ui import safe_rerun

# Configure the app once (must be called only once) and before any other Streamlit calls
st.set_page_config(page_title="The Turning Point", layout="wide", initial_sidebar_state="collapsed")

# Ensure session state defaults exist for all pages
init_session()
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
            # Immediately dispatch the password_reset page server-side so the
            # recovery link opens the correct UI even when client-side query
            # propagation is delayed.
            import runpy, os
            base_dir = os.path.dirname(__file__)
            candidate = os.path.join(base_dir, 'pages', 'password_reset.py')
            if os.path.isfile(candidate):
                runpy.run_path(candidate, run_name='__main__')
                st.stop()
        except Exception:
            # Fallback: set the page so the dispatcher may pick it up later
            try:
                st.session_state['page'] = 'password_reset'
                st.experimental_rerun()
            except Exception:
                pass
except Exception:
    pass
# Ensure a default `page` query param exists for unauthenticated users so
# Streamlit's multipage auto-loading doesn't pick a sidebar page on refresh.
if not st.session_state.get("authenticated"):
    # Ensure unauthenticated sessions land on the homepage. Set a session
    # key so our dispatcher will render `pages/homepage.py` on refresh.
    try:
        # Only set a default homepage when no `page` has already been chosen
        # (this allows explicit pages like `password_reset` to take precedence).
        if not st.session_state.get('page'):
            st.session_state['page'] = 'homepage'
            try:
                st.experimental_rerun()
            except Exception:
                pass
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

# Client-side redirect: if the browser landed on the root URL with a Supabase
# recovery token (either in the query string or fragment/hash), navigate the
# browser directly to `/password_reset` so the recovery link opens the correct
# UI even if server-side dispatch doesn't observe the query params immediately.
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

                // Check query string first
                const params = new URLSearchParams(window.location.search || '');
                const t = params.get('type');
                const token = params.get('access_token');
                if(t === 'recovery' && token){
                    const dest = '/password_reset?type=recovery&access_token=' + encodeURIComponent(token);
                    scheduleRedirect(dest);
                    return;
                }

                // If no query params, also inspect the fragment/hash (e.g. #access_token=...)
                if(window.location.hash){
                    const frag = window.location.hash.replace(/^#/, '');
                    const fparams = new URLSearchParams(frag);
                    const ft = fparams.get('type');
                    const ftoken = fparams.get('access_token');
                    if(ft === 'recovery' && ftoken){
                        const dest = '/password_reset?type=recovery&access_token=' + encodeURIComponent(ftoken);
                        // Try replacing URL repeatedly then navigate
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

# Ensure older code calling `st.experimental_rerun()` keeps working by
# providing a compatibility shim that points to our safe helper when
# Streamlit doesn't expose `experimental_rerun`.
try:
    if not hasattr(st, 'experimental_rerun'):
        setattr(st, 'experimental_rerun', safe_rerun)
except Exception:
    pass

# Dispatcher early so root app doesn't also render the same page (e.g. homepage)
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
        runpy.run_path(candidate, run_name="__main__")
        st.stop()
    except Exception:
        # Let the main dispatcher at the bottom show an error if needed
        pass

# Attempt early dispatch so the root app doesn't render the same page
_dispatch_page_early()

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
