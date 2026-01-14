import streamlit as st
from datetime import datetime
from utils.database import supabase
from utils.email import send_email

st.title("Tutor Confirmation — Admin")

if "admin" not in st.session_state:
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

st.markdown("Assign tutors to pending bookings, notify tutors to confirm, and finalize once tutors confirm.")

try:
    # Include a range of statuses so admin can assign and finalize
    statuses = ["Pending", "Assigned", "AwaitingTutorConfirmation", "TutorConfirmed", "Confirmed"]
    res = supabase.table("bookings").select("*").in_("status", statuses).order("exam_date").limit(500).execute()
    rows = res.data or []
except Exception as e:
    st.error(f"Could not load bookings: {e}")
    rows = []

if not rows:
    st.info("No relevant bookings found.")

def find_tutor(tutor_ref, booking=None):
    if not tutor_ref:
        return None
    keys_to_try = ["id", "tutor_id", "user_id", "email"]
    for k in keys_to_try:
        try:
            res = supabase.table('tutors').select('id,name,surname,phone,email').eq(k, tutor_ref).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    try:
        all_res = supabase.table('tutors').select('id,name,surname,phone,email').execute()
        tutors = all_res.data or []
    except Exception:
        tutors = []
    for t in tutors:
        if str(t.get('id')) == str(tutor_ref):
            return t
    if booking:
        candidates = []
        for field in ('tutor_name', 'tutor_fullname', 'tutor'):
            v = booking.get(field)
            if v:
                candidates.append(v.lower())
        for t in tutors:
            fullname = f"{t.get('name','')} {t.get('surname','')}".strip().lower()
            if fullname in candidates or any(c in fullname for c in candidates):
                return t
    return None

# Load tutors for dropdowns (fallback list used for assign UI)
try:
    t_res = supabase.table("tutors").select("id,name,surname,phone,email").order("name").execute()
    tutors = t_res.data or []
except Exception:
    tutors = []

def tutor_label(t):
    return f"{t.get('name','')} {t.get('surname','')} ({t.get('phone') or t.get('email') or 'no contact'})"

for b in rows:
    st.divider()
    booking_id = b.get('id')
    exam_date = b.get("exam_date") or "(no date)"
    start_time = b.get("start_time") or "(no time)"
    subject = b.get("subject") or "(no subject)"
    status = b.get("status") or "(no status)"

    st.subheader(f"{exam_date} {start_time} — {subject}")
    st.write(f"Status: {status}")

    # Current tutor info (if any)
    tutor_info = None
    if b.get('tutor_id'):
        try:
            t = find_tutor(b.get('tutor_id'), b)
            if t:
                tutor_info = (t.get('id'), f"{t.get('name','')} {t.get('surname','')}", t.get('phone') or t.get('email'))
        except Exception:
            tutor_info = None

    if tutor_info:
        st.write(f"Assigned tutor: {tutor_info[1]} — {tutor_info[2]}")

    # Assignment UI for Pending / Assigned / AwaitingTutorConfirmation
    if status in ["Pending", "Assigned", "AwaitingTutorConfirmation"]:
        # Build options
        options = ["(select tutor)"] + [tutor_label(t) for t in tutors]
        default_index = 0
        if tutor_info:
            # find index
            full_label = tutor_label(next((t for t in tutors if t.get('id') == tutor_info[0]), {}))
            try:
                default_index = options.index(full_label)
            except Exception:
                default_index = 0

        sel = st.selectbox("Select tutor to assign", options, index=default_index, key=f"select_{booking_id}")
        if sel and sel != "(select tutor)":
            # map selection back to tutor id
            sel_idx = options.index(sel) - 1
            selected_tutor = tutors[sel_idx]

            if st.button("Assign & Email Tutor", key=f"assign_{booking_id}"):
                # Safe update payload
                existing = set(b.keys() or [])
                candidate = {"tutor_id": selected_tutor.get('id'), "status": "AwaitingTutorConfirmation", "assigned_at": datetime.now().isoformat()}
                payload = {k: v for k, v in candidate.items() if k in existing}
                try:
                    if payload:
                        supabase.table('bookings').update(payload).eq('id', booking_id).execute()
                    # send email to tutor if we have an email
                    tutor_email = selected_tutor.get('email')
                    if tutor_email:
                        login_link = "https://your-app.example.com/tutor_login"
                        body = (
                            f"You have been assigned a new booking.\n\n"
                            f"Date: {exam_date}\n"
                            f"Time: {start_time}\n"
                            f"Subject: {subject}\n"
                            f"Please log in to the tutor portal and confirm this booking: {login_link}\n\n"
                            "Thanks,\nTurning Point"
                        )
                        email_res = send_email(tutor_email, "Please confirm assigned booking", body)
                        if email_res.get('error'):
                            st.warning(f"Assigned but failed to email tutor: {email_res.get('error')}")
                        else:
                            st.success("Tutor assigned and notified by email.")
                    else:
                        st.success("Tutor assigned. Tutor email not available — contact tutor manually.")

                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass
                except Exception as e:
                    st.error(f"Failed to assign tutor: {e}")

    # If tutor already confirmed via their portal, allow finalizing
    if status == "TutorConfirmed":
        if st.button("Finalize & Email Parent", key=f"finalize_{booking_id}"):
            now = datetime.now()
            existing = set(b.keys() or [])
            candidate = {"status": "Confirmed", "confirmed_at": now.isoformat()}
            payload = {k: v for k, v in candidate.items() if k in existing}
            try:
                if payload:
                    supabase.table('bookings').update(payload).eq('id', booking_id).execute()

                # Find parent email
                parent_email = None
                try:
                    p_res = supabase.table('parents').select('*').eq('id', b.get('parent_id')).execute()
                    p = (p_res.data or [None])[0]
                    if p and p.get('email'):
                        parent_email = p.get('email')
                except Exception:
                    parent_email = None

                # Tutor info for email
                tutor_name = tutor_info[1] if tutor_info else (b.get('tutor_id') or 'Tutor')
                tutor_contact = tutor_info[2] if tutor_info else 'no contact'

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
                    email_res = send_email(parent_email, "Booking Confirmed", body)
                    if email_res.get('error'):
                        st.warning(f"Confirmed but failed to send parent email: {email_res.get('error')}")
                    else:
                        st.success("Booking finalized and parent notified by email.")
                else:
                    st.success("Booking finalized. Parent email not found — contact parent manually.")

                try:
                    st.experimental_rerun()
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Failed to finalize booking: {e}")

    # Provide a Cancel option for any booking
    if st.button("Cancel Booking", key=f"cancel_{booking_id}"):
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

