import streamlit as st
st.set_page_config(page_title="Parent Profile")
from utils.database import supabase

# Make sure user is logged in
if "user" in st.session_state:
    user = st.session_state["user"]

    # Check if profile exists
    profile_res = supabase.table("parents").select("*").eq("user_id", user.id).execute()
    profile = profile_res.data[0] if profile_res.data else None

    if profile:
        st.success(f"Welcome back, {profile.get('parent_name')}!")
        # Debug: if parent_name or phone missing, show raw profile for inspection
        if not profile.get('parent_name') or not profile.get('phone'):
            with st.expander("Debug: parent profile record (missing name/phone)"):
                st.write(profile)

        st.subheader("Child Details")
        c_name, c_grade, c_school = st.columns([2,1,2])
        c_name.markdown(f"**Name**\n\n{profile.get('child_name', '—')}")
        c_grade.markdown(f"**Grade**\n\n{profile.get('grade', '—')}")
        c_school.markdown(f"**School**\n\n{profile.get('school', '—')}")

        st.markdown("---")

        # List parent's bookings (Pending / Confirmed)
        try:
            bookings_res = supabase.table("bookings").select("*").eq("parent_id", profile.get("id")).in_("status", ["Pending", "Confirmed"]).order("exam_date", desc=False).execute()
            bookings = bookings_res.data or []
        except Exception as e:
            st.error(f"Could not load bookings: {e}")
            bookings = []

        if bookings:
            st.subheader("Your Bookings")
            for b in bookings:
                # Format date and time safely
                exam_date = b.get("exam_date")
                start_time = b.get("start_time")
                subject = b.get("subject") or "(no subject)"
                status = b.get("status")
                status_label = "Booked" if status == "Confirmed" else "Pending"

                # attempt nicer formatting
                display_date = exam_date
                try:
                    # exam_date stored as ISO date string
                    from datetime import datetime
                    display_date = datetime.fromisoformat(exam_date).date().isoformat()
                except Exception:
                    pass

                display_time = start_time
                try:
                    from datetime import datetime
                    display_time = datetime.strptime(start_time, "%H:%M:%S").time().strftime("%H:%M")
                except Exception:
                    pass

                line = f"{display_date} {display_time} — {subject} ({status_label})"

                # If confirmed, attempt to show assigned tutor and contact
                if status == "Confirmed":
                    tutor_id = b.get("tutor_id")
                    if tutor_id:
                        try:
                            tutor_res = supabase.table("tutors").select("name,surname,phone,email").eq("id", tutor_id).execute()
                            if tutor_res.data:
                                t = tutor_res.data[0]
                                tutor_name = f"{t.get('name','')} {t.get('surname','')}".strip()
                                contact = t.get("phone") or t.get("email") or "no contact"
                                line = f"{line} — Tutor: {tutor_name} — {contact}"
                        except Exception:
                            # If tutor lookup fails, continue without contact info
                            pass

                # Render booking line with a small cancel button to the right
                cols = st.columns([9, 1])
                with cols[0]:
                    st.write(line)
                with cols[1]:
                    cancel_key = f"cancel_{b.get('id')}"
                    if st.button("❌", key=cancel_key):
                        # Cancellation logic: apply billing rule cutoff at 17:00 the day before
                        from datetime import datetime, timedelta, time as dt_time

                        cancel_time = datetime.now()
                        exam_date_raw = b.get("exam_date")
                        start_time_raw = b.get("start_time")
                        cutoff_applies = False
                        try:
                            # Parse stored date/time (ISO date and HH:MM:SS time)
                            exam_date_obj = datetime.fromisoformat(exam_date_raw).date()
                            start_time_obj = datetime.strptime(start_time_raw, "%H:%M:%S").time()
                            exam_dt = datetime.combine(exam_date_obj, start_time_obj)

                            cutoff = datetime.combine(exam_dt.date() - timedelta(days=1), dt_time(17, 0))
                            if cancel_time > cutoff:
                                cutoff_applies = True
                        except Exception:
                            # If parsing fails, we cannot compute cutoff — treat as no cutoff
                            cutoff_applies = False

                        # Update booking as cancelled in DB (only update existing columns)
                        try:
                            existing = set(b.keys() or [])
                            candidate = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
                            payload = {k: v for k, v in candidate.items() if k in existing}

                            if not payload:
                                st.error("Unable to cancel: bookings table missing cancel/status columns. Cancel manually in DB.")
                            else:
                                supabase.table("bookings").update(payload).eq("id", b.get("id")).execute()

                                if cutoff_applies:
                                    wa_number_display = "+27 82 883 6167"
                                    wa_link = "https://wa.me/27828836167"
                                    st.warning(f"Cancelled after 17:00 the day before — billing may apply. For emergencies after this cutoff please call or WhatsApp {wa_number_display}.")
                                    st.markdown(f"[Open WhatsApp →]({wa_link})")
                                else:
                                    st.success("Booking cancelled without penalty.")

                                try:
                                    st.experimental_rerun()
                                except Exception:
                                    pass
                        except Exception as e:
                            st.error(f"Failed to cancel booking: {e}")
        else:
            st.info("No pending or confirmed bookings found.")

        st.markdown("---")

        # Centered booking action: clickable icon + label
        b1, b2, b3 = st.columns([1,2,1])
        with b2:
            if st.button("📝  Proceed to Booking", key="parent_proceed_booking"):
                try:
                    st.switch_page("pages/parent_booking.py")
                except Exception:
                    st.experimental_rerun()
    else:
        st.warning("Please complete your profile to proceed.")

        # Attempt to locate an existing parent profile by other hints (email) and show debug
        try:
            user_email = getattr(user, 'email', None) or (user.get('email') if isinstance(user, dict) else None)
        except Exception:
            user_email = None
        if user_email:
            try:
                alt = supabase.table('parents').select('*').eq('email', user_email).execute()
                if alt.data:
                    with st.expander('Found parent record by email'):
                        st.write(alt.data[0])
            except Exception:
                pass

        parent_name = st.text_input("Parent Name")
        phone = st.text_input("Phone Number")
        child_name = st.text_input("Child Name")
        grade = st.text_input("Child Grade")
        school = st.text_input("Child School")

        if st.button("Save Profile"):
            if parent_name and phone and child_name and grade and school:
                insert_res = supabase.table("parents").insert({
                    "user_id": user.id,
                    "parent_name": parent_name,
                    "phone": phone,
                    "child_name": child_name,
                    "grade": grade,
                    "school": school
                }).execute()

                if getattr(insert_res, 'error', None) is None and insert_res.data:
                    st.success("Profile saved successfully! You can now book a reader/scribe.")
                    try:
                        st.experimental_rerun()
                    except Exception:
                        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                else:
                    st.error(f"Failed to save profile. Error: {getattr(insert_res, 'error', None)}")
            else:
                st.error("Please fill in all fields.")
else:
    st.info("Please log in first via the Parent Portal.")
