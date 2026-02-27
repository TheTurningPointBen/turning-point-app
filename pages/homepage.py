import streamlit as st

st.markdown(
    """
    <script>
    if (window.location.hash) {
        const hash = window.location.hash.substring(1);
        const url = new URL(window.location.href.split('#')[0]);
        const params = new URLSearchParams(hash);
        params.forEach((value, key) => {
            url.searchParams.set(key, value);
        });
        window.location.replace(url.toString());
    }
    </script>
    """,
    unsafe_allow_html=True
)

from utils.ui import hide_sidebar
import os
import runpy

# --- HARD EXIT FOR PASSWORD RECOVERY ---
qp = st.query_params

if qp.get("type") == "recovery" and qp.get("access_token"):
    st.switch_page("pages/password_reset.py")

hide_sidebar()

try:
    st.set_page_config(page_title="The Turning Point - Homepage", layout="wide", page_icon="🎈")
except Exception:
    pass

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
        max-width: 500px;
        width: 90%;
        height: auto;
    }
    
    /* Main Title Styling */
    h1 {
        color: #dc143c;
        font-weight: 700;
        text-align: center;
        font-size: 2.8rem;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Welcome Message */
    .welcome-message {
        text-align: center;
        font-size: 1.3rem;
        color: #555;
        margin-bottom: 3rem;
        padding: 1.5rem;
        background: white;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .welcome-message strong {
        color: #dc143c;
    }
    
    /* Tagline */
    .tagline {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        font-style: italic;
        margin-bottom: 3rem;
        padding: 1rem;
    }
    
    .tagline strong {
        color: #dc143c;
    }
    
    /* Role Card Container */
    .role-cards-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Portal Selection Title */
    .portal-title {
        text-align: center;
        font-size: 1.8rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 2rem;
    }
    
    /* Role Card Styling */
    .stButton > button {
        width: 100%;
        height: 220px;
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
        transform: translateY(-8px);
        box-shadow: 0 12px 30px rgba(220, 20, 60, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(-4px);
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
        padding-bottom: 3rem;
        max-width: 100%;
    }
    
    /* Balloon Animation */
    .balloon-decoration {
        font-size: 2rem;
        animation: float 3s ease-in-out infinite;
        display: inline-block;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-12px); }
    }
    
    /* Footer */
    .footer {
        text-align: center;
        margin-top: 4rem;
        padding: 2rem;
        color: #999;
        font-size: 0.9rem;
    }
    
    /* Recovery Link Styling */
    .stError {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Client-side fragment -> query string converter
try:
    st.markdown(
        """
        <script>
        (function() {
            try {
                const hash = window.location.hash || "";
                if (!hash) return;
                if (window.location.search.includes("from_fragment=1")) return;
                const params = new URLSearchParams(hash.slice(1));
                const type = params.get("type");
                const access_token = params.get("access_token") || params.get("token") || params.get("token_hash");
                if (type === "recovery" && access_token) {
                    const q = new URLSearchParams(window.location.search);
                    q.set("type", type);
                    q.set("access_token", access_token);
                    q.set("from_fragment", "1");
                    q.set("target", "password_reset");
                    const newUrl = window.location.origin + window.location.pathname + "?" + q.toString();
                    console.log('TP: merging fragment into query', {newUrl});
                    try { document.documentElement.setAttribute('data-tp-fragment','1'); } catch(e){}
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
    pass

try:
    qp = st.query_params or {}
except Exception:
    qp = {}

qp_type = (qp.get('type') or [None])[0]
qp_token = (qp.get('access_token') or [None])[0]
qp_from = (qp.get('from_fragment') or [None])[0]
qp_target = (qp.get('target') or [None])[0]

# Handle recovery links
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
                try:
                    dest = f"/password_reset?type=recovery&access_token={qp_token}"
                    st.markdown(f"<script>window.location.href='{dest}';</script>", unsafe_allow_html=True)
                    try:
                        st.stop()
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
    else:
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

# ===== LOGO HEADER =====
st.markdown("""
    <div class="logo-container">
        <img src="https://raw.githubusercontent.com/TheTurningPointBen/turning-point-app/main/logo.jpg" 
             alt="The Turning Point Logo"
             onerror="this.style.display='none'">
    </div>
""", unsafe_allow_html=True)

# ===== WELCOME MESSAGE =====
st.markdown("""
    <div class="welcome-message">
        Welcome to <strong>The Turning Point</strong> 🎈<br>
        <em>Educational & Emotional Support for Children</em>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="tagline">
        <span class="balloon-decoration">🎈</span> <strong>It's only up from HERE!</strong> <span class="balloon-decoration">🎈</span>
    </div>
""", unsafe_allow_html=True)

# ===== PORTAL SELECTION =====
st.markdown('<div class="portal-title">Select Your Portal</div>', unsafe_allow_html=True)

st.markdown('<div class="role-cards-container">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("👨‍👩‍👧\n\nParent Portal", key="homepage_parent"):
        try:
            st.switch_page("pages/parent.py")
        except Exception:
            st.session_state['page'] = 'parent'
            try:
                st.experimental_rerun()
            except Exception:
                pass

with col2:
    if st.button("🎓\n\nTutor Portal", key="homepage_tutor"):
        try:
            st.switch_page("pages/tutor_login.py")
        except Exception:
            st.session_state['page'] = 'tutor_login'
            try:
                st.experimental_rerun()
            except Exception:
                pass

with col3:
    if st.button("🔐\n\nAdmin Portal", key="homepage_admin"):
        try:
            st.switch_page("pages/admin.py")
        except Exception:
            st.session_state['page'] = 'admin'
            try:
                st.experimental_rerun()
            except Exception:
                pass

st.markdown('</div>', unsafe_allow_html=True)

# ===== FOOTER =====
st.markdown("""
    <div class="footer">
        <p>🎈 <strong>The Turning Point Pty Ltd</strong></p>
        <p>Educational & Emotional Support for Children | © 2024 All rights reserved.</p>
    </div>
""", unsafe_allow_html=True)
pass
