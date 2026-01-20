import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from datetime import date, datetime
import math
import pandas as pd
from utils.database import supabase

st.title("Admin Dashboard")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
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
    # Redirect to homepage and rerun so admin is taken to homepage after logout
    try:
        st.session_state['page'] = 'homepage'
        st.experimental_rerun()
    except Exception:
        try:
            st.markdown("<script>window.location.href='/'</script>", unsafe_allow_html=True)
        except Exception:
            pass

# Top icon navigation: Pending / Confirmed / Admin Area
if "admin_dashboard_view" not in st.session_state:
    st.session_state.admin_dashboard_view = "pending"

# Single-row layout: five equal columns across the page
col1, col2, col3, col4, col5, col6 = st.columns([1,1,1,1,1,1])
with col1:
    if st.button("📥 Pending", key="view_pending"):
        try:
            st.switch_page("pages/admin_pending_bookings.py")
        except Exception:
            st.session_state.admin_dashboard_view = "pending"
            try:
                st.experimental_rerun()
            except Exception:
                pass
with col2:
    if st.button("✅ Confirmed", key="view_confirmed"):
        try:
            st.switch_page("pages/admin_confirmed_bookings.py")
        except Exception:
            st.session_state.admin_dashboard_view = "confirmed"
            try:
                st.experimental_rerun()
            except Exception:
                pass
with col3:
    if st.button("👥 Tutor Profiles", key="view_tutor_profiles"):
        try:
            st.switch_page("pages/admin_tutor_profiles.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass
with col4:
    if st.button("✏️ Edit Bookings", key="view_tutor_confirmation"):
        try:
            st.switch_page("pages/admin_tutor_confirmation.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass
with col5:
    if st.button("⚙ Admin Area", key="view_area"):
        try:
            st.switch_page("pages/admin_admin_area.py")
        except Exception:
            try:
                st.session_state.admin_dashboard_view = "area"
                st.experimental_rerun()
            except Exception:
                pass
with col6:
    if st.button("🔒 Logout", key="admin_logout_icon"):
        st.session_state["_logout_pending"] = True

# Compact, professional styling for the top dashboard buttons (single horizontal row)
st.markdown(
    """
    <style>
    .compact-admin-row { display:flex; gap:10px; align-items:center; }
    .compact-admin-btn { padding:6px 12px !important; font-size:13px !important; border-radius:8px !important; background:#0d6efd !important; color:#fff !important; border: 0 !important; box-shadow: 0 2px 6px rgba(13,110,253,0.12) !important; height:36px !important; display:inline-flex !important; align-items:center !important; gap:8px !important; white-space:nowrap !important; }
    .compact-admin-btn:hover { background:#0b5ed7 !important; }
    .compact-admin-btn:active { transform: translateY(1px); }
    </style>
    <script>
    (function(){
        // Detect buttons by emoji (more robust than exact label match)
        const emojis = ['📥','✅','👥','📝','⚙'];
        const apply = ()=>{
            const btns = Array.from(document.querySelectorAll('button'));
            for(const b of btns){
                if(!b.innerText) continue;
                const txt = b.innerText.replace(/\s+/g,' ').trim();
                for(const e of emojis){
                    if(txt.indexOf(e) !== -1){
                        b.classList.add('compact-admin-btn');
                        b.style.whiteSpace = 'nowrap';
                        break;
                    }
                }
            }
        };
        // Run after render and when Streamlit updates
        setTimeout(apply, 150);
        const obs = new MutationObserver(()=> setTimeout(apply, 80));
        obs.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# Option to view past bookings from the Admin Area
show_past = st.checkbox("Show past bookings (last 7 days)", key="admin_show_past")

# Logout confirmation dialog
if st.session_state.get("_logout_pending"):
    st.warning("Do you wish to log out?")
    ycol, ncol = st.columns(2)
    with ycol:
        if st.button("Yes — Log out", key="admin_confirm_logout_yes"):
            st.session_state["_logout_confirmed"] = True
    with ncol:
        if st.button("No — Stay", key="admin_confirm_logout_no"):
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

# --- Build query ---
query = supabase.table("bookings").select("*")

# Apply view filter (Pending / Confirmed) from the top icons
view = st.session_state.get("admin_dashboard_view", "pending")
if view == "pending":
    query = query.eq("status", "Pending")
elif view == "confirmed":
    query = query.eq("status", "Confirmed")

# Exclude cancelled bookings (some DBs may not have a dedicated cancelled column)
try:
    query = query.neq("status", "Cancelled")
except Exception:
    # If the client or DB doesn't support `neq`, fall back to running the query as-is
    pass

res = query.order("start_time").execute()

# Show only bookings (Pending/Confirmed) occurring in the next 48 hours
from datetime import timedelta
now = datetime.now()
# Show only future bookings (from now) up to the next 48 hours
# If the admin requested past bookings, extend the window back 7 days
if st.session_state.get("admin_show_past"):
    start_window = now - timedelta(days=7)
else:
    start_window = now
cutoff = now + timedelta(hours=48)

bookings = res.data or []
upcoming = []
for b in bookings:
    try:
        date_str = b.get('exam_date')
        time_str = b.get('start_time') or '00:00:00'
        dt = datetime.combine(datetime.fromisoformat(date_str), datetime.strptime(time_str, "%H:%M:%S").time())
    except Exception:
        continue
    # Show bookings from now up to 48 hours from now (hide passed bookings)
    if start_window <= dt <= cutoff:
        upcoming.append((dt, b))

if not upcoming:
    st.info("No bookings pending/confirmed in the next 48 hours.")
else:
    upcoming.sort(key=lambda x: x[0])
    st.subheader(f"Bookings from {start_window.strftime('%d %b %Y %H:%M')} to {cutoff.strftime('%d %b %Y %H:%M')}")
    for dt, b in upcoming:
        st.divider()
        st.write(f"{dt.strftime('%d %b %Y %H:%M')} — {b.get('child_name')} — {b.get('subject')} ({b.get('status')})")
        st.write(f"School: {b.get('school')} | Duration: {b.get('duration')} mins | Role: {b.get('role_required')}")
        tutor_info = ''
        if b.get('tutor_id'):
            try:
                # robust lookup: try id/email then fallback to full table match
                def find_tutor_inline(tutor_ref, booking=None):
                    if not tutor_ref:
                        return None
                    for k in ('id','tutor_id','user_id','email'):
                        try:
                            r = supabase.table('tutors').select('name,surname,phone,email,id').eq(k, tutor_ref).execute()
                            if r.data:
                                return r.data[0]
                        except Exception:
                            pass
                    try:
                        allr = supabase.table('tutors').select('id,name,surname,phone,email').execute()
                        tutors_all = allr.data or []
                    except Exception:
                        tutors_all = []
                    for ttt in tutors_all:
                        if str(ttt.get('id')) == str(tutor_ref):
                            return ttt
                    if booking:
                        for field in ('tutor_name','tutor_fullname','tutor'):
                            v = booking.get(field)
                            if v:
                                v = v.lower()
                                for ttt in tutors_all:
                                    fullname = f"{ttt.get('name','')} {ttt.get('surname','')}".strip().lower()
                                    if v in fullname or fullname in v:
                                        return ttt
                    return None

                tt = find_tutor_inline(b.get('tutor_id'), b)
                if tt:
                    contact = tt.get('phone') or tt.get('email') or 'no contact'
                    tutor_info = f"Tutor: {tt.get('name')} {tt.get('surname')} — {contact}"
            except Exception:
                tutor_info = ''
        if tutor_info:
            st.write(tutor_info)

    # Grouping: show bookings per Tutor or Parent (selector moved above results)
