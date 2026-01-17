import streamlit as st
from utils.ui import hide_sidebar

# Apply global hide-sidebar config for consistent layout
hide_sidebar()
from datetime import datetime, timedelta
from utils.database import supabase
from utils.email import send_email

st.title("Admin Portal")

# Hide Streamlit Pages list in the sidebar for a cleaner admin login
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
                st.session_state["authenticated"] = True
                st.session_state["user"] = res.user
                st.session_state["role"] = "admin"
                st.session_state["email"] = getattr(res.user, 'email', None)
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

    # -------------------------
    # FORGOT PASSWORD
    # -------------------------
    with st.expander("Forgot password?"):
        fp_email = st.text_input("Enter your admin account email to receive reset instructions", key="admin_forgot_email")
        if st.button("Send reset email", key="admin_forgot_send"):
            if not fp_email:
                st.error("Please enter your email.")
            else:
                try:
                    try:
                        res = supabase.auth.reset_password_for_email(fp_email)
                    except Exception:
                        try:
                            res = supabase.auth.api.reset_password_for_email(fp_email)
                        except Exception:
                            res = None

                    if res is None:
                        st.warning("Password reset request could not be sent — please contact support.")
                    else:
                        st.success("If that email exists, password reset instructions have been sent.")
                except Exception as e:
                    st.error("Failed to request password reset. Please try again later.")
                    try:
                        st.exception(e)
                    except Exception:
                        pass

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

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
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

            # Notify parent by email with tutor details (if available)
            try:
                # fetch tutor contact details
                t_res = supabase.table('tutors').select('name,surname,phone,email').eq('id', tutor_id).execute()
                tutor_name = None
                tutor_contact = None
                if getattr(t_res, 'data', None):
                    t = t_res.data[0]
                    tutor_name = f"{t.get('name','')} {t.get('surname','')}".strip()
                    tutor_contact = t.get('phone') or t.get('email') or 'no contact'

                # fetch parent email
                p_res = supabase.table('parents').select('email').eq('id', booking.get('parent_id')).execute()
                parent_email = (p_res.data or [None])[0].get('email') if getattr(p_res, 'data', None) else None

                if parent_email:
                    body_lines = [
                        f"Your booking has been confirmed.",
                        f"Child: {booking.get('child_name')}",
                        f"Subject: {booking.get('subject')}",
                        f"Date: {booking.get('exam_date')}",
                        f"Start: {booking.get('start_time')}",
                    ]
                    if tutor_name:
                        body_lines.append(f"Tutor: {tutor_name}")
                    if tutor_contact:
                        body_lines.append(f"Contact: {tutor_contact}")

                    body_lines.append("\nPlease contact the tutor if you have any questions.\n\nThe Turning Point")
                    send_parent = send_email(parent_email, "Booking Confirmed", "\n".join(body_lines))
                    if send_parent.get('error'):
                        st.warning(f"Failed to send confirmation email to parent: {send_parent.get('error')}")
            except Exception:
                pass

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
