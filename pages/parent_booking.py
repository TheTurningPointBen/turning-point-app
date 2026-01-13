import streamlit as st
from datetime import datetime, timedelta
from utils.database import supabase
from utils.email import send_admin_email

if "user" not in st.session_state:
    st.error("Please log in first")
    st.stop()

# Get parent profile
user = st.session_state["user"]
profile_res = supabase.table("parents").select("*").eq("user_id", user.id).execute()
profile = profile_res.data[0]

st.header("Book a Reader / Scribe for your child")

# Form inputs
subject = st.text_input("Subject")
exam_date = st.date_input("Exam Date", min_value=datetime.today())
start_time = st.time_input("Start Time")
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

    if eligible_tutors:
        st.info(f"{len(eligible_tutors)} tutors match your role requirement.")
        for t in eligible_tutors:
            st.write(f"{t.get('name')} {t.get('surname')} — {t.get('town')} — {t.get('roles')}")
    else:
        st.info("No tutors currently match the selected role.")
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
if booking_dt < now + timedelta(hours=24):
    wa_number_display = "+27 82 883 5167"
    wa_link = "https://wa.me/27828835167"
    st.error(f"Bookings within 24 hours must be made via WhatsApp: {wa_number_display}")
    st.markdown(f"[Open WhatsApp chat →]({wa_link})")
    st.stop()

    # Determine which eligible tutors are actually available at the requested time.
    # Business decision: tutors are considered AVAILABLE by default unless they explicitly mark themselves unavailable
    # or they already have a conflicting booking. Therefore, start with all eligible tutors and only exclude conflicts.
    booking_date = exam_date
    start_dt = datetime.combine(booking_date, start_time)
    end_dt = start_dt + timedelta(minutes=(duration + extra_time))
    selected_tutor_id = None

    # Start with all eligible tutors
    available_tutors = list(eligible_tutors)

    try:
        final_tutors = []
        school = profile.get("school")

        for tutor in available_tutors:
            # Exclude tutors who already have a booking that conflicts with this requested slot
            booking_res = supabase.table("bookings") \
                .select("*") \
                .eq("tutor_id", tutor["id"]) \
                .eq("exam_date", booking_date.isoformat()) \
                .execute()

            conflict = False
            for b in (booking_res.data or []):
                try:
                    prev_start = datetime.combine(
                        booking_date,
                        datetime.strptime(b["start_time"], "%H:%M:%S").time()
                    )
                except Exception:
                    # if booking start_time parsing fails, skip that booking from conflict checks
                    continue

                prev_duration = int(b.get("duration") or 0)
                prev_extra = int(b.get("extra_time") or 0)
                prev_end = prev_start + timedelta(minutes=(prev_duration + prev_extra))

                buffer_end = prev_end + timedelta(minutes=90)

                # same school exception — no buffer
                if b.get("school") == school:
                    buffer_end = prev_end

                if start_dt < buffer_end:
                    conflict = True
                    break

            # Also exclude tutors who have an explicit unavailability entry covering this date/time
            try:
                unavail_res = supabase.table("tutor_unavailability") \
                    .select("*") \
                    .eq("tutor_id", tutor["id"]) \
                    .execute()

                for u in (unavail_res.data or []):
                    try:
                        u_start_date = datetime.fromisoformat(u.get("start_date")).date()
                        u_end_date = datetime.fromisoformat(u.get("end_date")).date()
                    except Exception:
                        continue

                    # if booking_date falls within the unavailability date range
                    if u_start_date <= booking_date <= u_end_date:
                        # if unavailability specifies times, compare times; otherwise treat whole day as unavailable
                        u_start_time = None
                        u_end_time = None
                        if u.get("start_time") and u.get("end_time"):
                            try:
                                u_start_time = datetime.strptime(u.get("start_time"), "%H:%M:%S").time()
                                u_end_time = datetime.strptime(u.get("end_time"), "%H:%M:%S").time()
                            except Exception:
                                u_start_time = None
                                u_end_time = None

                        if u_start_time and u_end_time:
                            # if requested slot overlaps the unavailable times
                            if not (end_dt.time() <= u_start_time or start_dt.time() >= u_end_time):
                                conflict = True
                                break
                        else:
                            # full-day unavailability
                            conflict = True
                            break
            except Exception:
                # if unavailability lookup fails, don't block the tutor based on unavailability
                pass

            if not conflict:
                final_tutors.append(tutor)

        if final_tutors:
            # STEP 5 — limit to top 5
            top_5 = final_tutors[:5]

            # STEP 6 — admin dropdown to select a tutor
            tutor_map = {
                f"{t['name']} {t['surname']} ({t.get('city') or t.get('town')})": t["id"]
                for t in top_5
            }

            selected = st.selectbox("Select Tutor", list(tutor_map.keys()))
            selected_tutor_id = tutor_map[selected]

            st.info(f"{len(top_5)} tutors available (showing top 5).")
            for t in top_5:
                st.write(f"{t.get('name')} {t.get('surname')} — {t.get('town')} — {t.get('roles')}")
        else:
            st.info("No tutors available at the requested time after applying buffer rules.")
    except Exception as e:
        st.error(f"Could not check tutor availability/conflicts: {e}")

if st.button("Book Exam"):

    if delta.total_seconds() < 24*3600:
        wa_number_display = "+27 82 883 5167"
        wa_link = "https://wa.me/27828835167"
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
        "end_time": end_dt.time().strftime("%H:%M:%S"),
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
