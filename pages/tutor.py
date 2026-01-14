import streamlit as st
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
    for k in list(st.session_state.keys()):
        if k != "_is_running":
            del st.session_state[k]
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.href='/'</script>", unsafe_allow_html=True)

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
        _logout()

# Upcoming Bookings
st.subheader("Upcoming Bookings")
try:
    b_res = supabase.table("bookings").select("*").eq("tutor_id", profile.get("id")).execute()
    now = datetime.now()
    upcoming = []
    if b_res.data:
        for b in b_res.data:
            slot = b.get("slot")
            try:
                slot_dt = datetime.strptime(slot, "%Y-%m-%d %H:%M")
            except Exception:
                slot_dt = None
            if slot_dt and slot_dt >= now:
                upcoming.append((slot_dt, b))

    if upcoming:
        upcoming.sort(key=lambda x: x[0])
        for slot_dt, b in upcoming:
            st.write(f"- {slot_dt.strftime('%Y-%m-%d %H:%M')} — {b.get('notes', '')}")
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
