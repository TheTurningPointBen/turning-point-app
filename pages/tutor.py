import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
st.set_page_config(page_title="Tutor Dashboard")
from datetime import datetime, date
from utils.database import supabase

st.title("Tutor Dashboard")

# -------------------------
# AUTH CHECK
# -------------------------
if "user" not in st.session_state:
    st.warning("Please login first.")
    try:
        st.switch_page("pages/tutor_login.py")
    except Exception:
        st.stop()

user = st.session_state.user

# fetch tutor profile
profile_res = supabase.table("tutors").select("*").eq("user_id", user.id).execute()
profile = profile_res.data[0] if profile_res.data else None

def _logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    # Clear session state (preserve any internal runner key)
    for k in list(st.session_state.keys()):
        if k != "_is_running":
            try:
                del st.session_state[k]
            except Exception:
                pass

    # Clear query params and redirect to app root to ensure a clean logout
    try:
        st.query_params = {}
    except Exception:
        pass

    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.href='/'</script>", unsafe_allow_html=True)
        st.stop()

if not profile:
    st.info("Please complete your tutor profile first.")
    if st.button("Go to My Tutor Profile"):
        try:
            st.switch_page("pages/tutor_profile.py")
        except Exception:
            st.experimental_rerun()
    st.stop()

# Icon navigation
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("👤\nMy Tutor Profile"):
        try:
            st.switch_page("pages/tutor_profile.py")
        except Exception:
            st.experimental_rerun()
with col2:
    if st.button("📅\nMy Bookings"):
        try:
            st.switch_page("pages/tutor_bookings.py")
        except Exception:
            st.experimental_rerun()
with col3:
    if st.button("❌\nUnavailability"):
        try:
            st.switch_page("pages/tutor_unavailability.py")
        except Exception:
            st.experimental_rerun()
with col4:
    if st.button("🔒\nLogout"):
        st.session_state["_logout_pending"] = True
        
    # Logout confirmation dialog
    if st.session_state.get("_logout_pending"):
        st.warning("Do you wish to log out?")
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button("Yes — Log out", key="confirm_logout_yes"):
                st.session_state["_logout_confirmed"] = True
        with no_col:
            if st.button("No — Stay logged in", key="confirm_logout_no"):
                st.session_state.pop("_logout_pending", None)
                try:
                    st.experimental_rerun()
                except Exception:
                    pass

# If the user confirmed logout, perform it here (ensures single-click logout)
if st.session_state.get("_logout_confirmed"):
    try:
        _logout()
    finally:
        st.session_state.pop("_logout_confirmed", None)

# Upcoming Bookings
st.subheader("Upcoming Bookings")
try:
    # Prefer tutor-specific bookings table if present, otherwise fall back to general bookings
    try:
        b_res = supabase.table("tutor_bookings").select("*").eq("tutor_id", profile.get("id")).execute()
        rows = b_res.data or []
    except Exception:
        b_res = supabase.table("bookings").select("*").eq("tutor_id", profile.get("id")).execute()
        rows = b_res.data or []

    now = datetime.now()
    upcoming = []
    for b in rows:
        # robustly handle different datetime representations
        slot = b.get("slot") or b.get("start_datetime") or None
        slot_dt = None
        if slot:
            try:
                slot_dt = datetime.strptime(slot, "%Y-%m-%d %H:%M")
            except Exception:
                try:
                    slot_dt = datetime.fromisoformat(slot)
                except Exception:
                    slot_dt = None

        # fallback to separate date/time fields
        if slot_dt is None:
            exam_date = b.get("exam_date")
            start_time = b.get("start_time")
            if exam_date:
                try:
                    time_part = start_time or '00:00:00'
                    if len(time_part.split(':')) == 2:
                        time_part = time_part + ':00'
                    slot_dt = datetime.fromisoformat(f"{exam_date}T{time_part}")
                except Exception:
                    slot_dt = None

        if slot_dt and slot_dt >= now:
            upcoming.append((slot_dt, b))

    if upcoming:
        upcoming.sort(key=lambda x: x[0])
        for slot_dt, b in upcoming:
            notes = b.get('notes') or b.get('subject') or ''
            st.write(f"- {slot_dt.strftime('%Y-%m-%d %H:%M')} — {notes}")
    else:
        st.info("No upcoming bookings.")
except Exception as e:
    st.error(f"Could not fetch bookings: {e}")

# Upcoming Unavailability
st.subheader("Upcoming Unavailability")
try:
    ua_res = supabase.table("tutor_unavailability").select("*").eq("tutor_id", profile.get("id")).order("start_date").execute()
    upcoming_ua = []
    if ua_res.data:
        for u in ua_res.data:
            try:
                end_d = datetime.fromisoformat(u.get("end_date"))
            except Exception:
                try:
                    end_d = datetime.strptime(u.get("end_date"), "%Y-%m-%d")
                except Exception:
                    end_d = None
            if end_d and end_d.date() >= date.today():
                upcoming_ua.append(u)

    if upcoming_ua:
        for u in upcoming_ua:
            times = "(full day)"
            if u.get("start_time") and u.get("end_time"):
                times = f"{u.get('start_time')} – {u.get('end_time')}"
            st.write(f"- {u.get('start_date')} → {u.get('end_date')} {times} — {u.get('reason', '')}")
    else:
        st.info("No upcoming unavailability.")
except Exception as e:
    st.error(f"Could not fetch unavailability: {e}")
