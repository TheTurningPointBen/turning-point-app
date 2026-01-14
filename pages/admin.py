import streamlit as st
st.set_page_config(page_title="Admin")
from datetime import datetime, timedelta
from utils.database import supabase

st.title("Admin Portal")

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    st.subheader("Admin Login")
    admin_email = st.text_input("Admin Email", key="admin_login_email")
    admin_password = st.text_input("Password", type="password", key="admin_login_pw")

    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": admin_email, "password": admin_password})
            if getattr(res, 'user', None):
                st.session_state["admin"] = res.user
                st.success("Admin logged in")
                try:
                    st.switch_page("pages/admin_dashboard.py")
                except Exception:
                    safe_rerun()
            else:
                st.error("Login failed. Check credentials or confirm email.")
                st.write(res)
        except Exception as e:
            st.error("Login exception. Check console for details.")
            st.exception(e)

with tab2:
    st.subheader("Admin Registration")
    reg_email = st.text_input("Email", key="admin_reg_email")
    reg_password = st.text_input("Password", type="password", key="admin_reg_pw")
    confirm_pw = st.text_input("Confirm Password", type="password", key="admin_reg_confirm")

    if st.button("Register"):
        if reg_password != confirm_pw:
            st.error("Passwords do not match.")
        else:
            try:
                res = supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                if getattr(res, 'user', None):
                    st.success("Registration successful. Please confirm the email before logging in.")
                else:
                    st.error("Registration may have failed; see response below.")
                    st.write(res)
            except Exception as e:
                st.error("Registration failed. Email may already exist.")
                st.exception(e)

if "admin" not in st.session_state:
    st.stop()

# --- FETCH PENDING BOOKINGS ---
st.header("Pending Bookings")

bookings_res = supabase.table("bookings").select("*").eq("status", "Pending").execute()

if not bookings_res.data:
    st.info("No pending bookings")
    st.stop()

for booking in bookings_res.data:
    st.divider()
    st.subheader(f"{booking['child_name']} – {booking['subject']}")
    st.write(f"School: {booking['school']}")
    st.write(f"Date: {booking['exam_date']}")
    st.write(f"Start: {booking['start_time']} | Duration: {booking['duration']} mins")
    st.write(f"Role required: {booking['role_required']}")

    exam_date = booking.get("exam_date")
    try:
        start_time = datetime.strptime(booking["start_time"], "%H:%M:%S").time()
    except Exception:
        start_time = None

    # --- FETCH SUITABLE TUTORS ---
    tutors_res = supabase.table("tutors").select("*").eq("approved", True).execute()

    suitable_tutors = []

    for tutor in (tutors_res.data or []):
        roles = tutor.get("roles")
        if roles == "Both" or booking["role_required"] in roles:
            suitable_tutors.append(tutor)

    # Limit to top 5
    suitable_tutors = suitable_tutors[:5]

    if not suitable_tutors:
        st.warning("No suitable tutors available")
        continue

    tutor_options = {f"{t['name']} {t['surname']} ({t.get('city','')})": t["id"] for t in suitable_tutors}

    selected_tutor = st.selectbox("Assign Tutor", options=list(tutor_options.keys()), key=str(booking.get("id")))

    if st.button("Confirm Booking", key=f"confirm_{booking.get('id')}"):
        tutor_id = tutor_options[selected_tutor]

        update_res = supabase.table("bookings").update({"status": "Confirmed", "tutor_id": tutor_id}).eq("id", booking["id"]).execute()

        if getattr(update_res, 'error', None) is None:
            st.success("Booking confirmed")
            safe_rerun()
        else:
            st.error(update_res.error)

    # Admin cancel button
    if st.button("Cancel Booking", key=f"admin_cancel_{booking.get('id')}"):
        try:
            cancel_time = datetime.now()
            # compute exam datetime if available
            exam_date = booking.get("exam_date")
            try:
                start_time = datetime.strptime(booking["start_time"], "%H:%M:%S").time()
                exam_dt = datetime.combine(datetime.fromisoformat(exam_date), start_time)
                hours_before = (exam_dt - cancel_time).total_seconds() / 3600
            except Exception:
                hours_before = None

            # Build update payload only with keys present on this booking row
            existing = set(booking.keys() or [])
            candidate = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
            payload = {k: v for k, v in candidate.items() if k in existing}

            if not payload:
                st.error("Unable to cancel: bookings table missing cancel/status columns. Cancel manually in DB.")
            else:
                supabase.table("bookings").update(payload).eq("id", booking.get("id")).execute()

                if hours_before is not None and hours_before < 12:
                    st.warning("Cancelled within 12 hours — billing may apply.")
                else:
                    st.success("Booking cancelled without penalty.")

                safe_rerun()
        except Exception as e:
            st.error(f"Failed to cancel booking: {e}")
