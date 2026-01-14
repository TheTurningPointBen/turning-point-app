import streamlit as st
from datetime import datetime
from utils.database import supabase
from utils.email import send_admin_email

st.title("Booking")

if "user" not in st.session_state:
    st.info("Please log in via the Parent Portal first.")
else:
    user = st.session_state["user"]

    # fetch parent profile
    profile_res = supabase.table("parents").select("*").eq("user_id", user.id).execute()
    parent = profile_res.data[0] if profile_res.data else None

    if not parent:
        st.warning("Please complete your profile on the Parent Profile page before booking.")
    else:
        st.subheader("Available slots")
        # Simple static slots — replace with dynamic schedule as needed
        slots = [
            "2026-01-20 09:00",
            "2026-01-20 10:00",
            "2026-01-20 11:00",
            "2026-01-21 09:00",
            "2026-01-21 10:00",
        ]

        slot = st.selectbox("Choose a slot", slots)
        notes = st.text_area("Notes (optional)")

        if st.button("Book slot"):
            try:
                # check if slot already booked
                check = supabase.table("bookings").select("*").eq("slot", slot).execute()
                if check.data:
                    st.error("Slot already booked. Choose another slot.")
                else:
                    insert = supabase.table("bookings").insert({
                        "user_id": user.id,
                        "parent_id": parent.get("id"),
                        "slot": slot,
                        "notes": notes
                    }).execute()

                    if getattr(insert, 'error', None) is None and insert.data:
                        st.success("Booking created successfully.")

                        # Notify admin
                        subject_line = f"New slot booking: {slot} by {user.email}"
                        body = (
                            f"Parent email: {user.email}\n"
                            f"Parent id: {user.id}\n"
                            f"Slot: {slot}\n"
                            f"Notes: {notes}\n"
                        )
                        email_res = send_admin_email(subject_line, body)
                        if email_res.get("error"):
                            st.warning(f"Booking saved but failed to send admin email: {email_res.get('error')}")
                    else:
                        st.error(f"Failed to create booking: {getattr(insert, 'error', None)}")
            except Exception as e:
                st.error(f"Booking exception: {e}")
                st.exception(e)

        st.markdown("---")
        st.subheader("Your bookings")
        try:
            b_res = supabase.table("bookings").select("*").eq("user_id", user.id).execute()
            if b_res.data:
                for b in b_res.data:
                    slot = b.get('slot')
                    notes = b.get('notes')

                    cancelled = b.get('cancelled')
                    cancelled_at = b.get('cancelled_at')

                    if cancelled:
                        st.write(f"- {slot} — {notes} — CANCELLED at {cancelled_at}")
                        continue

                    st.write(f"- {slot} — {notes}")

                    # parse slot (expected format: YYYY-MM-DD HH:MM)
                    try:
                        exam_time = datetime.strptime(slot, "%Y-%m-%d %H:%M")
                    except Exception:
                        exam_time = None

                    if st.button("Cancel Booking", key=f"cancel_{b.get('id')}"):
                        cancel_time = datetime.now()
                        if exam_time:
                            hours_before = (exam_time - cancel_time).total_seconds() / 3600
                        else:
                            hours_before = None

                        # Attempt to update booking with cancelled fields; only update existing columns
                        try:
                            existing = set(b.keys() or [])
                            candidate = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
                            payload = {k: v for k, v in candidate.items() if k in existing}

                            if not payload:
                                st.error("Unable to cancel: bookings table missing cancel/status columns. Cancel manually in DB.")
                            else:
                                supabase.table("bookings").update(payload).eq("id", b.get('id')).execute()

                                if hours_before is not None and hours_before < 12:
                                    st.warning("Cancelled within 12 hours — billing applies.")
                                else:
                                    st.success("Booking cancelled without penalty.")
                        except Exception as e:
                            st.error(f"Failed to cancel booking: {e}")
            else:
                st.write("No bookings yet.")
        except Exception as e:
            st.error(f"Could not fetch bookings: {e}")