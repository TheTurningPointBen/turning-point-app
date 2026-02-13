import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from datetime import datetime
from utils.database import supabase

st.title("Pending Bookings — Admin")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

# Top-left small Back button that returns to the Admin Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_dashboard_pending"):
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


def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)


st.markdown("---")

# Fetch pending bookings
try:
    bookings_res = supabase.table("bookings").select("*").eq("status", "Pending").order("exam_date").execute()
    bookings = bookings_res.data or []
except Exception as e:
    st.error(f"Could not load pending bookings: {e}")
    st.stop()

# Discard pending bookings that are already past their date/time
from datetime import datetime
now = datetime.now()
filtered = []
for booking in bookings:
    try:
        date_str = booking.get('exam_date')
        time_str = booking.get('start_time') or '00:00:00'
        dt = datetime.combine(datetime.fromisoformat(date_str), datetime.strptime(time_str, "%H:%M:%S").time())
    except Exception:
        # If parsing fails, keep the booking so admins can inspect it
        filtered.append(booking)
        continue
    # only keep pending bookings that are now or in the future
    if dt >= now:
        filtered.append(booking)

bookings = filtered

if not bookings:
    st.info("No pending bookings")
    st.stop()

for booking in bookings:
    st.divider()
    st.subheader(f"{booking.get('child_name')} — {booking.get('subject')}")
    st.write(f"School: {booking.get('school')}")
    st.write(f"Date: {booking.get('exam_date')}")
    st.write(f"Start: {booking.get('start_time')} | Duration: {booking.get('duration')} mins")
    st.write(f"Role required: {booking.get('role_required')}")

    # find suitable tutors
    try:
        tutors_res = supabase.table("tutors").select("*").eq("approved", True).execute()
        suitable = []
        def _normalize(r):
            if not r:
                return r
            r = str(r)
            if "Both" in r:
                return "Both"
            return r

        def role_matches(tutor_role, required_role):
            tr = _normalize(tutor_role)
            rr = _normalize(required_role)
            if not tr or not rr:
                return False
            if tr == rr:
                return True
            if tr == "All of the Above":
                return True
            if rr in ("Reader", "Scribe") and tr == "Both":
                return True
            return False

        def _language_column_for(subject_text: str):
            if not subject_text:
                return None
            s = subject_text.strip().lower()
            mapping = {
                'afrikaans': 'afrikaans',
                'isizulu': 'isizulu',
                'zulu': 'isizulu',
                'setswana': 'setswana',
                'isixhosa': 'isixhosa',
                'xhosa': 'isixhosa',
                'french': 'french'
            }
            return mapping.get(s)

        def _tutor_is_available(tutor_id, exam_date_obj, start_time_obj, duration_minutes):
            try:
                u_res = supabase.table('tutor_unavailability').select('*').eq('tutor_id', tutor_id).lte('start_date', exam_date_obj.isoformat()).gte('end_date', exam_date_obj.isoformat()).execute()
                entries = u_res.data or []
                if not entries:
                    return True
                import datetime as _dt
                bstart_dt = _dt.datetime.combine(exam_date_obj, start_time_obj)
                bend_dt = bstart_dt + _dt.timedelta(minutes=duration_minutes)
                for e in entries:
                    if not e.get('start_time') or not e.get('end_time'):
                        return False
                    try:
                        es = _dt.datetime.strptime(e.get('start_time'), '%H:%M:%S').time()
                        ee = _dt.datetime.strptime(e.get('end_time'), '%H:%M:%S').time()
                    except Exception:
                        return False
                    estart_dt = _dt.datetime.combine(exam_date_obj, es)
                    eend_dt = _dt.datetime.combine(exam_date_obj, ee)
                    latest_start = max(bstart_dt, estart_dt)
                    earliest_end = min(bend_dt, eend_dt)
                    overlap = (earliest_end - latest_start).total_seconds()
                    if overlap > 0:
                        return False
                return True
            except Exception:
                return False

        # parse booking exam date and start_time
        try:
            exam_date_obj = datetime.fromisoformat(booking.get('exam_date')).date() if booking.get('exam_date') else None
        except Exception:
            exam_date_obj = None
        try:
            start_time = datetime.strptime(booking.get('start_time'), "%H:%M:%S").time() if booking.get('start_time') else None
        except Exception:
            start_time = None

        lang_col = _language_column_for(booking.get('subject'))

        for t in (tutors_res.data or []):
            if not role_matches(t.get('roles'), booking.get('role_required')):
                continue
            if lang_col and not t.get(lang_col):
                continue
            if start_time and exam_date_obj:
                if not _tutor_is_available(t.get('id'), exam_date_obj, start_time, booking.get('duration') or 60):
                    continue
            suitable.append(t)
        suitable = suitable[:5]
    except Exception:
        suitable = []

    if not suitable:
        st.warning("No suitable tutors available")
        continue

    tutor_options = {f"{t.get('name')} {t.get('surname')} ({t.get('city','')})": t.get('id') for t in suitable}
    key = f"assign_{booking.get('id')}"
    selected = st.selectbox("Assign Tutor", options=list(tutor_options.keys()), key=key)

    if st.button("Confirm Booking", key=f"confirm_{booking.get('id')}"):
        tutor_id = tutor_options.get(selected)
        try:
            update_res = supabase.table("bookings").update({"status": "Confirmed", "tutor_id": tutor_id}).eq("id", booking.get("id")).execute()
            if getattr(update_res, 'error', None) is None:
                st.success("Booking confirmed")

                # Fetch tutor and parent records to send confirmation emails
                try:
                    tres = supabase.table('tutors').select('*').eq('id', tutor_id).execute()
                    tutor = (tres.data or [None])[0]
                except Exception:
                    tutor = None

                try:
                    pres = supabase.table('parents').select('*').eq('id', booking.get('parent_id')).execute()
                    parent = (pres.data or [None])[0]
                except Exception:
                    parent = None

                # Email tutor about the assignment
                try:
                    if tutor and tutor.get('email'):
                        from utils.email import send_email
                        t_email = tutor.get('email')
                        t_name = f"{tutor.get('name') or ''} {tutor.get('surname') or ''}".strip()
                        subj = f"New booking assigned: {booking.get('child_name') or 'Child'} — {booking.get('subject') or ''}"
                        body = (
                            f"Hello {t_name or 'Tutor'},\n\n"
                            f"You have been assigned to a booking:\n"
                            f"Child: {booking.get('child_name')}\n"
                            f"Subject: {booking.get('subject')}\n"
                            f"Date: {booking.get('exam_date')}\n"
                            f"Start Time: {booking.get('start_time')}\n"
                            f"Duration: {booking.get('duration')} minutes\n"
                            f"Parent contact (email): {parent.get('email') if parent else 'N/A'}\n"
                            f"Parent phone: {parent.get('phone') if parent else 'N/A'}\n\n"
                            f"Please log in to the admin panel to view details.\n"
                        )
                        try:
                            mail = send_email(t_email, subj, body)
                            if mail.get('ok'):
                                st.info(f"Notification emailed to tutor {t_name}.")
                            else:
                                st.warning(f"Failed to email tutor: {mail.get('error')}")
                        except Exception:
                            st.warning("Failed to send email to tutor (exception)")
                except Exception:
                    pass

                # Email parent confirming tutor assignment
                try:
                    if parent and parent.get('email'):
                        from utils.email import send_email
                        p_email = parent.get('email')
                        tutor_display = (f"{tutor.get('name') or ''} {tutor.get('surname') or ''}".strip()) if tutor else str(tutor_id)
                        subj = f"Booking confirmed — Tutor assigned: {tutor_display}"
                        body = (
                            f"Hello {parent.get('parent_name') or ''},\n\n"
                            f"Your booking for {booking.get('child_name') or ''} on {booking.get('exam_date')} at {booking.get('start_time')} has been confirmed.\n"
                            f"Assigned tutor: {tutor_display}\n"
                            f"Tutor email: {tutor.get('email') if tutor else 'N/A'}\n"
                            f"Tutor phone: {tutor.get('phone') if tutor else 'N/A'}\n\n"
                            f"If you have any questions, reply to this email or contact admin.\n"
                        )
                        try:
                            mail = send_email(p_email, subj, body)
                            if mail.get('ok'):
                                st.info("Confirmation emailed to parent.")
                            else:
                                st.warning(f"Failed to email parent: {mail.get('error')}")
                        except Exception:
                            st.warning("Failed to send email to parent (exception)")
                except Exception:
                    pass

                safe_rerun()
            else:
                st.error(update_res)
        except Exception as e:
            st.error(f"Failed to confirm booking: {e}")

    if st.button("Cancel Booking", key=f"cancel_{booking.get('id')}"):
        try:
            cancel_time = datetime.now()
            # Build update payload only including columns that exist on this booking row
            existing = set(booking.keys() or [])
            candidate = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
            payload = {k: v for k, v in candidate.items() if k in existing}

            if not payload:
                st.error("Unable to cancel: the bookings table does not expose cancellable fields. Please cancel via the admin dashboard or update the booking status manually in the database.")
            else:
                supabase.table("bookings").update(payload).eq("id", booking.get('id')).execute()
                st.success("Booking cancelled")
                safe_rerun()
        except Exception as e:
            st.error(f"Failed to cancel booking: {e}")
