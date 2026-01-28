import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from datetime import datetime
from utils.database import supabase
from utils.email import send_email

st.title("Edit Confirmed Bookings")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

# Top-left small Back button that returns to the Admin Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_dashboard_confirmation"):
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

st.markdown("Edit or Cancel Bookings")

try:
    # Load bookings that have an allocated tutor (we're showing tutors who are booked)
    statuses = ["Assigned", "AwaitingTutorConfirmation", "TutorConfirmed", "Confirmed"]
    res = supabase.table("bookings").select("*").in_("status", statuses).order("exam_date").limit(500).execute()
    rows = res.data or []
    # Filter to entries that actually have a tutor allocated
    rows = [r for r in rows if r.get('tutor_id')]
    # Exclude bookings that have already passed
    from datetime import datetime
    now = datetime.now()
    filtered_rows = []
    for r in rows:
        try:
            date_str = r.get('exam_date')
            time_str = r.get('start_time') or '00:00:00'
            dt = datetime.combine(datetime.fromisoformat(date_str), datetime.strptime(time_str, "%H:%M:%S").time())
        except Exception:
            # if parsing fails, keep the row
            filtered_rows.append(r)
            continue
        if dt >= now:
            filtered_rows.append(r)

    rows = filtered_rows
except Exception as e:
    st.error(f"Could not load bookings: {e}")
    rows = []

if not rows:
    st.info("No upcoming bookings found with an allocated tutor.")

def find_tutor(tutor_ref, booking=None):
    if not tutor_ref:
        return None
    keys_to_try = ["id", "tutor_id", "user_id", "email"]
    for k in keys_to_try:
        try:
            res = supabase.table('tutors').select('*').eq(k, tutor_ref).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    try:
        all_res = supabase.table('tutors').select('*').execute()
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
    school = b.get('school') or b.get('location') or '(no school)'

    st.subheader(f"{exam_date} {start_time} — {subject}")

    # Current tutor info (if any) - run lookup first so it's available for the summary
    tutor_info = None
    if b.get('tutor_id'):
        try:
            t = find_tutor(b.get('tutor_id'), b)
            if t:
                tutor_info = (t.get('id'), f"{t.get('name','')} {t.get('surname','')}", t.get('phone') or t.get('email'))
        except Exception:
            tutor_info = None

    # Client / Tutor / School summary line for quick scanning
    student = b.get('child_name') or b.get('student_name') or b.get('student') or b.get('child') or b.get('pupil') or '(no student)'
    if tutor_info:
        tutor_display = f"{tutor_info[1]}"
    else:
        # try to resolve tutor_id using cached tutors list before falling back to raw id/fields
        tutor_display = None
        try:
            t_match = next((t for t in (tutors or []) if str(t.get('id')) == str(b.get('tutor_id'))), None)
            if t_match:
                tutor_display = f"{t_match.get('name','')} {t_match.get('surname','')}".strip()
        except Exception:
            t_match = None
        # If still not resolved, try a direct DB lookup by id
        if not tutor_display and b.get('tutor_id'):
            try:
                direct = supabase.table('tutors').select('name,surname,phone,email').eq('id', b.get('tutor_id')).execute()
                if direct.data:
                    d = direct.data[0]
                    tutor_display = f"{d.get('name','')} {d.get('surname','')}".strip()
            except Exception:
                pass
        if not tutor_display:
            tutor_display = b.get('tutor_name') or b.get('tutor_fullname') or b.get('tutor') or str(b.get('tutor_id') or '(no tutor)')

    st.write(f"Client: {student} | Tutor: {tutor_display} | School: {school}")
    st.write(f"Status: {status}")

    # Action buttons: Edit / Cancel / Finalize (if tutor confirmed)
    action_col1, action_col2, action_col3 = st.columns([1,1,1])
    with action_col1:
        if st.button("Edit Booking", key=f"edit_{booking_id}"):
            st.session_state[f"editing_{booking_id}"] = True
    with action_col2:
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
    with action_col3:
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

    # Allow admin to edit the tutor profile directly
    if b.get('tutor_id'):
        tutor_edit_btn_col, _ = st.columns([1, 8])
        with tutor_edit_btn_col:
            if st.button("Edit Tutor Profile", key=f"edit_tutor_profile_{booking_id}"):
                # open inline tutor editor for this tutor id
                st.session_state[f"editing_tutor_{b.get('tutor_id')}"] = True

    # Inline Tutor edit form
    tutor_id_for_edit = b.get('tutor_id')
    if tutor_id_for_edit and st.session_state.get(f"editing_tutor_{tutor_id_for_edit}"):
        try:
            t_res = supabase.table('tutors').select('*').eq('id', tutor_id_for_edit).execute()
            tutor = (t_res.data or [None])[0]
        except Exception as e:
            st.error(f"Failed to load tutor: {e}")
            tutor = None

        if tutor:
            st.markdown('---')
            st.subheader(f"Edit tutor profile: {tutor.get('name') or ''} {tutor.get('surname') or ''}")
            with st.form(key=f"edit_tutor_inline_{tutor_id_for_edit}"):
                name = st.text_input("First name", value=tutor.get('name') or "")
                surname = st.text_input("Surname", value=tutor.get('surname') or "")
                phone = st.text_input("Phone", value=tutor.get('phone') or "")
                email = st.text_input("Email", value=tutor.get('email') or "")
                city = st.text_input("City", value=tutor.get('city') or "")
                roles = st.text_input("Roles (Reader/Scribe/Both/Invigilator/Prompter/All of the Above)", value=tutor.get('roles') or "")
                approved = st.checkbox("Approved", value=bool(tutor.get('approved')))
                notes = st.text_area("Notes", value=tutor.get('notes') or "")

                st.markdown("---")
                st.subheader("Languages")
                afrikaans = st.checkbox("Afrikaans", value=bool(tutor.get('afrikaans')))
                isizulu = st.checkbox("IsiZulu", value=bool(tutor.get('isizulu')))
                setswana = st.checkbox("Setswana", value=bool(tutor.get('setswana')))
                isixhosa = st.checkbox("IsiXhosa", value=bool(tutor.get('isixhosa')))
                french = st.checkbox("French", value=bool(tutor.get('french')))

                save = st.form_submit_button("Save tutor profile")
                cancel = st.form_submit_button("Cancel")

                if cancel:
                    st.session_state.pop(f"editing_tutor_{tutor_id_for_edit}", None)
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass

                if save:
                    # Build payload and store in session for confirmation modal
                    payload = {}
                    existing_keys = set(tutor.keys())
                    fields = {
                        'name': name,
                        'surname': surname,
                        'phone': phone,
                        'email': email,
                        'city': city,
                        'roles': roles,
                        'approved': approved,
                        'notes': notes,
                        'afrikaans': bool(afrikaans),
                        'isizulu': bool(isizulu),
                        'setswana': bool(setswana),
                        'isixhosa': bool(isixhosa),
                        'french': bool(french),
                    }
                    for k, v in fields.items():
                        if k in existing_keys:
                            payload[k] = v

                    if not payload:
                        st.info("No updatable columns found for this tutor.")
                    else:
                        # Save pending payload in session_state and show confirmation modal below
                        pending_key = f"pending_tutor_update_{tutor_id_for_edit}"
                        st.session_state[pending_key] = payload
                        st.session_state[f"pending_tutor_name_{tutor_id_for_edit}"] = f"{tutor.get('name','')} {tutor.get('surname','')}"
                        try:
                            st.experimental_rerun()
                        except Exception:
                            pass

        # Confirmation modal: if a pending payload exists, prompt admin to confirm
        pending_key = f"pending_tutor_update_{tutor_id_for_edit}"
        if st.session_state.get(pending_key):
            payload = st.session_state.get(pending_key)
            pending_name = st.session_state.get(f"pending_tutor_name_{tutor_id_for_edit}")
            with st.modal("Confirm tutor update"):
                st.write(f"You are about to update the tutor profile: **{pending_name}**")
                st.write("Proposed changes:")
                st.json(payload)
                col_confirm, col_cancel = st.columns([1,1])
                with col_confirm:
                    if st.button("Confirm changes", key=f"confirm_tutor_update_{tutor_id_for_edit}"):
                        try:
                            upd = supabase.table('tutors').update(payload).eq('id', tutor_id_for_edit).execute()
                            if getattr(upd, 'error', None) is None:
                                st.success("Tutor profile updated")
                                # clear pending and editing flags
                                st.session_state.pop(pending_key, None)
                                st.session_state.pop(f"pending_tutor_name_{tutor_id_for_edit}", None)
                                st.session_state.pop(f"editing_tutor_{tutor_id_for_edit}", None)
                                try:
                                    st.experimental_rerun()
                                except Exception:
                                    pass
                            else:
                                st.error(f"Update failed: {getattr(upd, 'error', upd)}")
                        except Exception as e:
                            st.error(f"Failed to update tutor: {e}")
                with col_cancel:
                    if st.button("Cancel", key=f"cancel_tutor_update_{tutor_id_for_edit}"):
                        st.session_state.pop(pending_key, None)
                        st.session_state.pop(f"pending_tutor_name_{tutor_id_for_edit}", None)
                        try:
                            st.experimental_rerun()
                        except Exception:
                            pass

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

    # Edit form: shown when editing flag is set for this booking
    if st.session_state.get(f"editing_{booking_id}"):
        with st.form(key=f"edit_form_{booking_id}"):
            st.write("Edit booking details")
            # parse exam_date into a date input if possible
            try:
                date_val = datetime.fromisoformat(b.get('exam_date')).date()
            except Exception:
                try:
                    date_val = datetime.strptime(b.get('exam_date') or '', "%Y-%m-%d").date()
                except Exception:
                    date_val = None

            new_date = st.date_input("Date", value=date_val)
            # time as text field to avoid parsing inconsistencies
            new_time = st.text_input("Start time (HH:MM or HH:MM:SS)", value=b.get('start_time') or "07:45")
            new_subject = st.text_input("Subject", value=b.get('subject') or "")

            # tutor selection (default to current tutor)
            tutor_options = [tutor_label(t) for t in tutors]
            current_label = ""
            if tutor_info:
                current_label = tutor_label(next((t for t in tutors if t.get('id') == tutor_info[0]), {}))
            if current_label in tutor_options:
                default_idx = tutor_options.index(current_label)
            else:
                default_idx = 0
            sel_idx = st.selectbox("Change allocated tutor", options=tutor_options, index=default_idx, key=f"edit_select_{booking_id}")

            submitted = st.form_submit_button("Save changes")
            cancelled_edit = st.form_submit_button("Cancel edit")

            if cancelled_edit:
                st.session_state.pop(f"editing_{booking_id}", None)
                try:
                    st.experimental_rerun()
                except Exception:
                    pass

            if submitted:
                try:
                    selected_tutor = tutors[tutor_options.index(sel_idx)] if sel_idx in tutor_options else None
                    existing = set(b.keys() or [])
                    candidate = {
                        "exam_date": new_date.isoformat() if new_date else None,
                        "start_time": new_time,
                        "subject": new_subject,
                        "tutor_id": selected_tutor.get('id') if selected_tutor else b.get('tutor_id'),
                        "status": "Assigned",
                        "assigned_at": datetime.now().isoformat(),
                    }
                    payload = {k: v for k, v in candidate.items() if k in existing}
                    if payload:
                        supabase.table('bookings').update(payload).eq('id', booking_id).execute()

                        # notify new tutor if email available
                        if selected_tutor and selected_tutor.get('email'):
                            tutor_email = selected_tutor.get('email')
                            login_link = "https://your-app.example.com/tutor_login"
                            body = (
                                f"You have been assigned a booking (updated by admin).\n\n"
                                f"Date: {candidate.get('exam_date')}\n"
                                f"Time: {candidate.get('start_time')}\n"
                                f"Subject: {candidate.get('subject')}\n"
                                f"Please log in to confirm: {login_link}\n\nThanks,\nTurning Point"
                            )
                            try:
                                send_email(tutor_email, "Assigned booking (updated)", body)
                            except Exception:
                                pass

                        st.success("Booking updated.")
                        st.session_state.pop(f"editing_{booking_id}", None)
                        try:
                            st.experimental_rerun()
                        except Exception:
                            pass
                    else:
                        st.error("Could not update booking: DB missing expected columns.")
                except Exception as e:
                    st.error(f"Failed to save changes: {e}")

