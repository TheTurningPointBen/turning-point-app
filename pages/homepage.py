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
    st.set_page_config(page_title="The Turning Point - Homepage", layout="centered", page_icon="🎈")
except Exception:
    pass

# ===== CUSTOM CSS - FIXED SPACING & CENTERING =====
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
    
    /* FIXED: Reduce all padding to fit on one page */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1200px;
    }
    
    /* Logo Container - FIXED */
    .logo-container {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
        background: white;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
    
    .logo-container img {
        max-width: 400px;
        width: 85%;
        height: auto;
        display: block;
        margin: 0 auto;
    }
    
    /* Welcome Message - Compact */
    .welcome-message {
        text-align: center;
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 1rem;
        padding: 0.8rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .welcome-message strong {
        color: #dc143c;
    }
    
    /* Tagline - Compact */
    .tagline {
        text-align: center;
        color: #666;
        font-size: 1rem;
        font-style: italic;
        margin-bottom: 1.5rem;
        padding: 0.5rem;
    }
    
    .tagline strong {
        color: #dc143c;
    }
    
    /* Portal Selection Title */
    .portal-title {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 1.5rem;
    }
    
    /* FIXED: Center the portal buttons */
    [data-testid="column"] {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 0.5rem;
    }
    
    /* Role Card Styling - Compact but still nice */
    .stButton > button {
        width: 100%;
        max-width: 280px;
        height: 180px;
        background: white;
        border: 3px solid #e0e0e0;
        border-radius: 15px;
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
        transition: all 0.3s ease;
        box-shadow: 0 3px 12px rgba(0,0,0,0.1);
        display: block;
        margin: 0 auto;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #dc143c 0%, #a10000 100%);
        color: white;
        border-color: #dc143c;
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(220, 20, 60, 0.35);
    }
    
    .stButton > button:active {
        transform: translateY(-2px);
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Balloon Animation */
    .balloon-decoration {
        font-size: 1.5rem;
        animation: float 3s ease-in-out infinite;
        display: inline-block;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }
    
    /* Footer - Compact */
    .footer {
        text-align: center;
        margin-top: 2rem;
        padding: 1rem;
        color: #999;
        font-size: 0.85rem;
    }
    
    /* Recovery Link Styling */
    .stError {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    /* Remove extra spacing from Streamlit */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.5rem;
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

# ===== LOGO HEADER - USING STREAMLIT IMAGE =====
# Display logo using st.image for better compatibility
import base64
from PIL import Image

try:
    # Try multiple logo locations
    logo_displayed = False
    logo_paths = [
        'logo.jpg',
        'assets/logo.jpg', 
        'static/logo.jpg',
        '/mnt/user-data/uploads/1772188401219_TTP_Logo.jpg'
    ]
    
    for logo_path in logo_paths:
        try:
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            st.image(logo_path, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            logo_displayed = True
            break
        except:
            continue
    
    # If no local file works, try to use uploaded image from context
    if not logo_displayed:
        try:
            # Try to load from uploaded files
            uploaded_logo = '/mnt/user-data/uploads/1772188401219_TTP_Logo.jpg'
            img = Image.open(uploaded_logo)
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            st.image(img, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            logo_displayed = True
        except:
            pass
    
    # Final fallback - text version
    if not logo_displayed:
        st.markdown("""
            <div class="logo-container" style="padding: 1.5rem;">
                <h1 style="color: #dc143c; margin: 0; font-size: 2rem;">🎈 The Turning Point</h1>
                <p style="color: #666; margin: 0.5rem 0 0 0; font-size: 1rem;">Educational & Emotional Support for Children</p>
            </div>
        """, unsafe_allow_html=True)
        
except Exception as e:
    # Show text version if anything fails
    st.markdown("""
        <div class="logo-container" style="padding: 1.5rem;">
            <h1 style="color: #dc143c; margin: 0; font-size: 2rem;">🎈 The Turning Point</h1>
            <p style="color: #666; margin: 0.5rem 0 0 0; font-size: 1rem;">Educational & Emotional Support for Children</p>
        </div>
    """, unsafe_allow_html=True)

# ===== WELCOME MESSAGE - Compact =====
st.markdown("""
    <div class="welcome-message">
        Welcome to <strong>The Turning Point</strong> — Educational & Emotional Support for Children
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="tagline">
        <span class="balloon-decoration">🎈</span> <strong>It's only up from HERE!</strong> <span class="balloon-decoration">🎈</span>
    </div>
""", unsafe_allow_html=True)

# ===== PORTAL SELECTION =====
st.markdown('<div class="portal-title">Select Your Portal</div>', unsafe_allow_html=True)

# Create 5 columns with more space on left to push buttons right
col_spacer1, col1, col2, col3, col_spacer2 = st.columns([1.5, 2, 2, 2, 0.5])

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

# ===== FOOTER - Compact =====
st.markdown("""
    <div class="footer">
        <strong>The Turning Point Education Pty Ltd</strong> | Educational & Emotional Support for Children | © 2004
    </div>
""", unsafe_allow_html=True)
True)
