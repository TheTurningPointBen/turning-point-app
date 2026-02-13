import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from datetime import datetime
from utils.database import supabase
from utils.email import send_email, send_mailgun_email

st.title("Awaiting Tutor Confirmation — Admin")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

# Top-left small Back button that returns to the Admin Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_dashboard_awaiting"):
        st.switch_page("pages/admin_dashboard.py")

    st.markdown(
        """
        <style>
        .admin-back-space{height:4px}
        </style>
        <div class="admin-back-space"></div>
        <script>
        (function(){
            const label = '⬅️ Back';
            const apply = ()=>{
                const btns = Array.from(document.querySelectorAll('button'));
                for(const b of btns){
                    if(b.innerText && b.innerText.trim()===label){
                        b.style.background = '#0d6efd';
                        b.style.color = '#ffffff';
                        b.style.padding = '4px 8px';
                        b.style.borderRadius = '6px';
                        b.style.border = '0';
                        b.style.fontWeight = '600';
                        b.style.boxShadow = 'none';
                        b.style.cursor = 'pointer';
                        b.style.fontSize = '12px';
                        b.style.lineHeight = '16px';
                        b.style.display = 'inline-block';
                        b.style.margin = '0 8px 0 0';
                        b.style.verticalAlign = 'middle';
                        break;
                    }
                }
            };
            setTimeout(apply, 200);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

st.markdown("Bookings that have been allocated to a tutor but are waiting for the tutor to confirm. Admins can Hard Confirm (notify parent) or Cancel here.")

try:
    # Find bookings that have a tutor assigned but haven't been finalized
    statuses = ["AwaitingTutorConfirmation", "Assigned"]
    res = supabase.table("bookings").select("*").in_("status", statuses).order("exam_date").limit(500).execute()
    bookings = res.data or []
except Exception as e:
    st.error(f"Could not load awaiting bookings: {e}")
    bookings = []

if not bookings:
    st.info("No bookings awaiting tutor confirmation.")

for b in bookings:
    st.divider()
    booking_id = b.get("id")
    exam_date = b.get("exam_date") or "(no date)"
    start_time = b.get("start_time") or "(no time)"
    subject = b.get("subject") or "(no subject)"
    status = b.get("status") or "(no status)"

    st.subheader(f"{exam_date} {start_time} — {subject}")
    st.write(f"Status: {status}")

    # Tutor details
    tutor_info = None
    if b.get("tutor_id"):
        try:
            t_res = supabase.table("tutors").select("name,surname,phone,email").eq("id", b.get("tutor_id")).execute()
            t = (t_res.data or [None])[0]
            if t:
                tutor_info = (f"{t.get('name','')} {t.get('surname','')}".strip(), t.get('phone') or t.get('email') or 'no contact')
        except Exception:
            tutor_info = None

    if tutor_info:
        st.write(f"Tutor: {tutor_info[0]} — {tutor_info[1]}")
    else:
        st.write(f"Tutor ID: {b.get('tutor_id')}")

    cols = st.columns([1,1])
    # Hard Confirm: immediately mark Confirmed and email parent
    with cols[0]:
        if st.button("✅ Hard Confirm", key=f"hard_{booking_id}"):
            now = datetime.now()
            existing = set(b.keys() or [])
            candidate = {"status": "Confirmed", "confirmed_at": now.isoformat()}
            payload = {k: v for k, v in candidate.items() if k in existing}
            try:
                if payload:
                    supabase.table("bookings").update(payload).eq("id", booking_id).execute()

                # Lookup parent email
                parent_email = None
                try:
                    p_res = supabase.table("parents").select("*").eq("id", b.get("parent_id")).execute()
                    p = (p_res.data or [None])[0]
                    if p and p.get("email"):
                        parent_email = p.get("email")
                except Exception:
                    parent_email = None

                tutor_name = tutor_info[0] if tutor_info else (b.get('tutor_id') or 'Tutor')
                tutor_contact = tutor_info[1] if tutor_info else 'no contact'

                if parent_email:
                    body = (
                        f"Your Exam/Test booking has been confirmed.\n\n"
                        f"Date: {exam_date}\n"
                        f"Time: {start_time}\n"
                        f"Subject: {subject}\n"
                        f"Tutor: {tutor_name}\n"
                        f"Contact: {tutor_contact}\n\n"
                        "Please contact the tutor if you have any questions.\n\nThe Turning Point"
                    )
                    email_res = send_mailgun_email(parent_email, "Booking Confirmed", body)
                    if email_res.get('error'):
                        st.warning(f"Confirmed but failed to send parent email: {email_res.get('error')}")
                    else:
                        st.success("Booking hard-confirmed and parent notified by email.")
                else:
                    st.success("Booking hard-confirmed. Parent email not found — contact parent manually.")

                try:
                    st.experimental_rerun()
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Failed to hard-confirm booking: {e}")

    # Cancel button
    with cols[1]:
        if st.button("❌ Cancel Booking", key=f"cancel_{booking_id}"):
            try:
                cancel_time = datetime.now()
                existing = set(b.keys() or [])
                candidate = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
                payload = {k: v for k, v in candidate.items() if k in existing}
                if not payload:
                    st.error("Unable to cancel: bookings table missing cancel/status columns. Cancel manually in DB.")
                else:
                    supabase.table("bookings").update(payload).eq("id", booking_id).execute()
                    st.success("Booking cancelled")
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"Failed to cancel booking: {e}")
