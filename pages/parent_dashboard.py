import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Parent Dashboard")
except Exception:
    pass
from utils.database import supabase

st.title("Parent Dashboard")

if "user" not in st.session_state:
    st.warning("Please log in first.")
    try:
        st.switch_page("pages/parent.py")
    except Exception:
        st.stop()

def _logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for k in list(st.session_state.keys()):
        if k != "_is_running":
            try:
                del st.session_state[k]
            except Exception:
                pass
    try:
        st.experimental_set_query_params()
    except Exception:
        pass
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.href='/'</script>", unsafe_allow_html=True)

# Icon row: Profile / Make a Booking / Bookings
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    if st.button("👤 Profile", key="parent_profile_icon"):
        try:
            st.switch_page("pages/parent_profile.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass
with col2:
    if st.button("➕ Make a Booking", key="parent_make_booking_icon"):
        try:
            st.switch_page("pages/parent_booking.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass
with col3:
    if st.button("📚 Bookings", key="parent_bookings_icon"):
        try:
            st.switch_page("pages/parent_bookings.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass
with col4:
    if st.button("🔒 Logout", key="parent_logout_icon"):
        st.session_state["_logout_pending"] = True

_css_js = '''
<style>
.compact-parent-btn { padding:8px 14px !important; font-size:14px !important; border-radius:10px !important; background:#0d6efd !important; color:#fff !important; border:0 !important; box-shadow:0 2px 6px rgba(13,110,253,0.12) !important; height:44px !important; display:inline-flex !important; align-items:center !important; gap:8px !important; }
.compact-parent-btn:hover { background:#0b5ed7 !important; }
</style>
<script>
(function(){
    const emojis = ['👤','➕','📚'];
    const apply = ()=>{
        const btns = Array.from(document.querySelectorAll('button'));
        for(const b of btns){
            if(!b.innerText) continue;
            const txt = b.innerText.replace(/\s+/g,' ').trim();
            for(const e of emojis){
                if(txt.indexOf(e) !== -1){
                    b.classList.add('compact-parent-btn');
                    b.style.whiteSpace = 'nowrap';
                    break;
                }
            }
        }
    };
    setTimeout(apply, 150);
    const obs = new MutationObserver(()=> setTimeout(apply, 80));
    obs.observe(document.body, { childList: true, subtree: true });
})();
</script>
'''

st.markdown(_css_js, unsafe_allow_html=True)

st.markdown("---")
st.write("Use the icons above to manage your profile and bookings.")

# Logout confirmation dialog
if st.session_state.get("_logout_pending"):
    st.warning("Do you wish to log out?")
    ycol, ncol = st.columns(2)
    with ycol:
        if st.button("Yes — Log out", key="parent_confirm_logout_yes"):
            st.session_state["_logout_confirmed"] = True
    with ncol:
        if st.button("No — Stay", key="parent_confirm_logout_no"):
            st.session_state.pop("_logout_pending", None)
            try:
                st.experimental_rerun()
            except Exception:
                pass

# Perform logout if confirmed (single-click)
if st.session_state.get("_logout_confirmed"):
    try:
        _logout()
    finally:
        st.session_state.pop("_logout_confirmed", None)

# Hide non-parent pages from the sidebar for logged-in parents
if st.session_state.get("role") == "parent" or "user" in st.session_state:
    st.markdown(
        """
        <script>
        (function(){
            const allowed = ['Parent','Parent Portal','Parent Dashboard','Parent Profile','Parent Booking','Parent Your Bookings','Your Bookings','Profile','Bookings','Booking'];
            const hideNonParent = ()=>{
                try{
                    const sidebar = document.querySelector('aside');
                    if(!sidebar) return;
                    const links = sidebar.querySelectorAll('a');
                    links.forEach(a=>{
                        const txt = (a.innerText||a.textContent||'').trim();
                        const keep = allowed.some(k=> txt.indexOf(k)!==-1);
                        if(!keep){
                            const node = a.closest('div');
                            if(node) node.style.display='none';
                        }
                    });
                }catch(e){}
            };
            setTimeout(hideNonParent, 200);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
