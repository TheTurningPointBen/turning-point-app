```python
import streamlit as st
st.set_page_config(page_title="Parent Dashboard")
from utils.database import supabase

st.title("Parent Dashboard")

if "user" not in st.session_state:
    st.warning("Please log in first.")
    try:
        st.switch_page("pages/parent.py")
    except Exception:
        st.stop()

# Icon row: Profile / Make a Booking / Bookings
col1, col2, col3 = st.columns([1,1,1])
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
            st.switch_page("pages/parent_profile.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass

# Compact styling for parent dashboard icons
st.markdown(
    '''
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
    ''',
    unsafe_allow_html=True,
)

st.markdown("---")
st.write("Use the icons above to manage your profile and bookings.")

```
