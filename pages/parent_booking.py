import streamlit as st
from datetime import datetime, timedelta, time
from utils.database import supabase
from utils.email import send_admin_email

if "user" not in st.session_state:
    st.error("Please log in first")
    st.stop()

# Get parent profile
user = st.session_state["user"]
profile_res = supabase.table("parents").select("*").eq("user_id", user.id).execute()
profile = profile_res.data[0]

# Top-left Back button (styled) to return to parent profile
back_col, _ = st.columns([1, 9])
with back_col:
        if st.button("⬅️  Back to Profile"):
                st.switch_page("pages/parent_profile.py")

        # Apply inline styling to the rendered button via JS for a clean horizontal look
        st.markdown(
                """
                <style>
                /* Fallback minimal spacing so layout stays consistent */
                .parent-booking-back-space{height:8px}
                </style>
                <div class="parent-booking-back-space"></div>
                <script>
                (function(){
                    const label = '⬅️  Back to Profile';
                    const apply = ()=>{
                        const btns = Array.from(document.querySelectorAll('button'));
                                for(const b of btns){
                                    if(b.innerText && b.innerText.trim()===label){
                                        b.style.background = '#0d6efd';
                                        b.style.color = '#ffffff';
                                        b.style.padding = '6px 10px';
                                        b.style.borderRadius = '6px';
                                        b.style.border = '0';
                                        b.style.fontWeight = '600';
                                        b.style.boxShadow = 'none';
                                        b.style.cursor = 'pointer';
                                        b.style.fontSize = '13px';
                                        b.style.lineHeight = '18px';
                                        b.style.display = 'inline-block';
                                        b.style.margin = '4px 0';
                                        b.style.verticalAlign = 'middle';
                                        break;
                                    }
                                }
                    };
                    // Run after a short delay to ensure Streamlit has rendered the button
                    setTimeout(apply, 200);
                })();
                </script>
                """,
                unsafe_allow_html=True,
        )

st.header("Book a Reader / Scribe for your child")

# Form inputs
subject = st.text_input("Subject")
exam_date = st.date_input("Exam Date", min_value=datetime.today())
start_time = st.time_input("Start Time", value=time(7, 45))
duration = st.number_input("Duration (minutes)", min_value=30, max_value=180, value=60)
extra_time = st.number_input("Extra Time (minutes)", min_value=0, max_value=60, value=0)
role_required = st.selectbox("Role Required", ["Reader", "Scribe", "Both"]) 

# Show tutors who are approved and match the required role
try:
    tutors_res = supabase.table("tutors") \
        .select("*") \
        .eq("approved", True) \
        .execute()

    eligible_tutors = [
        t for t in (tutors_res.data or [])
        if t.get("roles") in [role_required, "Both"]
    ]

    # Tutor listings are admin-facing; do not show tutor counts or lists to parents.
except Exception as e:
    st.error(f"Could not load tutors: {e}")

# Booking rules
booking_dt = datetime.combine(exam_date, start_time)
now = datetime.now()

if booking_dt < now:
    st.error("Cannot book for a past time.")
    st.stop()

# time delta between requested booking and now
delta = booking_dt - now

# Business rule: bookings within 24 hours must be made via WhatsApp
# Compute booking date/time values used later and leave tutor assignment to admin.
booking_date = exam_date
start_dt = datetime.combine(booking_date, start_time)
end_dt = start_dt + timedelta(minutes=(duration + extra_time))
selected_tutor_id = None

if booking_dt < now + timedelta(hours=24):
    wa_number_display = "+27 82 883 6167"
    wa_link = "https://wa.me/27828836167"
    st.error(f"Bookings within 24 hours must be made via WhatsApp: {wa_number_display}")
    st.markdown(f"[Open WhatsApp chat →]({wa_link})")
    st.stop()

col1, col2 = st.columns([1,1])


def _insert_booking(add_another=False):
    if delta.total_seconds() < 24*3600:
        wa_number_display = "+27 82 883 6167"
        wa_link = "https://wa.me/27828836167"
        st.warning(f"You can still submit, but admin will require WhatsApp confirmation via {wa_number_display}.")
        st.markdown(f"[Open WhatsApp chat →]({wa_link})")

    insert_res = supabase.table("bookings").insert({
        "parent_id": profile["id"],
        "child_name": profile["child_name"],
        "grade": profile["grade"],
        "school": profile["school"],
        "subject": subject,
        "role_required": role_required,
        "exam_date": exam_date.isoformat(),
        "start_time": start_time.strftime("%H:%M:%S"),
        "duration": duration,
        "extra_time": extra_time,
        "tutor_id": selected_tutor_id
    }).execute()

    if getattr(insert_res, 'error', None) is None and insert_res.data:
        st.success("Booking submitted! Admin will confirm your tutor.")

        # Notify admin if SMTP is configured
        subject_line = f"New booking: {profile.get('child_name')} — {subject}"
        body = (
            f"Parent: {user.email}\n"
            f"Child: {profile.get('child_name')}\n"
            f"Grade: {profile.get('grade')}\n"
            f"School: {profile.get('school')}\n"
            f"Subject: {subject}\n"
            f"Role Required: {role_required}\n"
            f"Exam Date: {exam_date.isoformat()}\n"
            f"Start Time: {start_time.strftime('%H:%M:%S')}\n"
            f"Duration: {duration} min\n"
            f"Extra Time: {extra_time} min\n"
        )
        email_res = send_admin_email(subject_line, body)
        if email_res.get("error"):
            st.warning(f"Booking created but failed to send admin email: {email_res.get('error')}")

        # Show confirmation with selected tutor (if any)
        from utils.email import send_email

        if selected_tutor_id:
            try:
                tutor_res = supabase.table("tutors").select("name,surname,phone,email").eq("id", selected_tutor_id).execute()
                if tutor_res.data:
                    t = tutor_res.data[0]
                    contact = t.get("phone") or t.get("email") or "no contact"
                    st.success(f"Tutor assigned: {t.get('name')} {t.get('surname')} — {contact}")

                    # Send confirmation to parent
                    parent_email = user.email
                    tutor_name = f"{t.get('name')} {t.get('surname')}"
                    start_str = start_time.strftime("%H:%M:%S")
                    end_str = end_dt.time().strftime("%H:%M:%S")
                    send_parent = send_email(
                        parent_email,
                        "Reader / Scribe Booking Confirmed",
                        f"""
Your booking has been confirmed.

Tutor: {tutor_name}
Date: {booking_date.isoformat()}
Time: {start_str} – {end_str}
School: {profile.get('school')}

Cancellations within 12 hours will still be billed.

The Turning Point
"""
                    )
                    if send_parent.get("error"):
                        st.warning(f"Failed to send confirmation email to parent: {send_parent.get('error')}")

                    # Send assignment email to tutor
                    tutor_email = t.get("email")
                    if tutor_email:
                        send_tutor = send_email(
                            tutor_email,
                            "New Booking Assigned",
                            f"""
You have been assigned a booking.

Date: {booking_date.isoformat()}
Time: {start_str} – {end_str}
School: {profile.get('school')}

Please confirm availability.

The Turning Point
"""
                        )
                        if send_tutor.get("error"):
                            st.warning(f"Failed to send assignment email to tutor: {send_tutor.get('error')}")
                else:
                    st.info("Booking created; a tutor was selected but details are unavailable.")
            except Exception as e:
                st.warning(f"Booking created — couldn't fetch tutor details: {e}")
        else:
            st.info("Booking created. No tutor selected; admin will assign one.")

            # Notify parent that booking was created but no tutor assigned yet
            try:
                parent_email = user.email
                start_str = start_time.strftime("%H:%M:%S")
                end_str = end_dt.time().strftime("%H:%M:%S")
                send_parent = send_email(
                    parent_email,
                    "Reader / Scribe Booking Submitted",
                    f"""
Your booking has been submitted and is awaiting tutor assignment.

Date: {booking_date.isoformat()}
Time: {start_str} – {end_str}
School: {profile.get('school')}

Admin will assign a tutor and notify you.

The Turning Point
"""
                )
                if send_parent.get("error"):
                    st.warning(f"Failed to send submission email to parent: {send_parent.get('error')}")
            except Exception as e:
                st.warning(f"Booking created — couldn't send parent email: {e}")
    else:
        st.error(f"Booking failed: {getattr(insert_res, 'error', None)}")


_do_save = col1.button("💾  Save Booking")
_do_save_add = col2.button("➕  Save & Add Another")

if _do_save:
    _insert_booking(add_another=False)

if _do_save_add:
    _insert_booking(add_another=True)
    try:
        st.experimental_rerun()
    except Exception:
        pass

# Note: Back/Logout button removed per user request
