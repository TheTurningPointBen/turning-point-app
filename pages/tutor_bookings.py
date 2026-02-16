import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Tutor Bookings")
except Exception:
    pass
from datetime import datetime
from utils.database import supabase
import os
from utils.email import send_email, send_admin_email, _get_sender


def find_parent(parent_ref, booking=None):
    """Robust parent lookup: try by id, user_id, or fallback to scanning parents table.
    Returns parent dict or None.
    """
    if not parent_ref and not booking:
        return None

    # Try by id
    try:
        if parent_ref:
            r = supabase.table('parents').select('id,parent_name,phone,email,school,user_id').eq('id', parent_ref).execute()
            if r.data:
                return r.data[0]
    except Exception:
        pass

    # Try by user_id if booking contains a user reference
    try:
        if booking:
            for key in ('parent_user_id','parent_user','user_id'):
                v = booking.get(key)
                if v:
                    r = supabase.table('parents').select('id,parent_name,phone,email,school,user_id').eq('user_id', v).execute()
                    if r.data:
                        return r.data[0]
    except Exception:
        pass

    # Fallback: fetch all parents and try to match by multiple hints with scoring
    try:
        allr = supabase.table('parents').select('id,parent_name,name,phone,mobile,email,school,child_name,child_firstname,child_lastname').execute()
        parents = allr.data or []
    except Exception:
        parents = []

    # If we have a parent_ref try several id-like columns first
    id_columns = ['id', 'parent_id', 'user_id', 'uid']
    if parent_ref:
        for col in id_columns:
            try:
                r = supabase.table('parents').select('*').eq(col, parent_ref).execute()
                if r.data:
                    return r.data[0]
            except Exception:
                pass

    # Prepare booking hints
    booking_parent_name = (booking.get('parent_name') if booking else '') or (booking.get('parent') if booking else '') or ''
    booking_parent_name = booking_parent_name.strip().lower() if booking_parent_name else ''
    booking_child = (booking.get('child_name') or booking.get('child') or '').strip().lower() if booking else ''
    booking_parent_email = (booking.get('parent_email') or booking.get('email') or '').strip().lower() if booking else ''
    booking_parent_phone = (booking.get('parent_phone') or booking.get('phone') or '').strip() if booking else ''

    # Score parents by matching hints
    best = (None, 0)
    for p in parents:
        score = 0
        # exact id match
        try:
            if parent_ref and str(p.get('id')) == str(parent_ref):
                score += 50
        except Exception:
            pass

        # parent name match
        pname = (p.get('parent_name') or p.get('name') or '').strip().lower()
        if booking_parent_name and pname and booking_parent_name == pname:
            score += 30

        # email match
        pemail = (p.get('email') or '').strip().lower()
        if booking_parent_email and pemail and booking_parent_email == pemail:
            score += 40

        # phone partial match (last 6 digits)
        pphone = (p.get('phone') or p.get('mobile') or '').strip()
        if booking_parent_phone and pphone and booking_parent_phone[-6:] and pphone.endswith(booking_parent_phone[-6:]):
            score += 25

        # child name token match
        pchild = (p.get('child_name') or p.get('child_firstname') or p.get('child_lastname') or '').strip().lower()
        if booking_child and pchild:
            # split tokens and award points for overlap
            b_tokens = [t for t in booking_child.split() if t]
            p_tokens = [t for t in pchild.split() if t]
            common = sum(1 for t in b_tokens if any(t == pt or t in pt or pt in t for pt in p_tokens))
            score += common * 10

        if score > best[1]:
            best = (p, score)

    # Return best match if score positive
    if best[0] and best[1] > 0:
        return best[0]

    return None

st.title("My Bookings")

if "user" not in st.session_state:
    st.warning("Please login first.")
    try:
        st.switch_page("pages/tutor_login.py")
    except Exception:
        st.stop()

user = st.session_state.user

# fetch tutor profile
profile_res = supabase.table("tutors").select("*").eq("user_id", user.id).execute()
profile = profile_res.data[0] if profile_res.data else None

# Top-left Back button (small) to return to Tutor Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_tutor_dashboard_bookings"):
        try:
            st.switch_page("pages/tutor.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass

    st.markdown(
        """
        <style>
        .tutor-back-space{height:4px}
        </style>
        <div class="tutor-back-space"></div>
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

if not profile:
    st.warning("Please complete your tutor profile first.")
    st.stop()

try:
    # Be defensive: some DB schemas use `slot`, others use `exam_date` + `start_time`.
    b_res = supabase.table("bookings").select("*").eq("tutor_id", profile.get("id")).execute()
    rows = b_res.data or []
    if not rows:
        st.info("No bookings assigned to you yet.")
    else:
        # Build sortable list using available date/time fields
        parsed = []
        for b in rows:
            slot = b.get('slot')
            exam_date = b.get('exam_date')
            start_time = b.get('start_time')
            notes = b.get('notes') or ''
            cancelled = b.get('cancelled')
            status = b.get('status')

            dt = None
            # Prefer explicit slot if present and parseable
            if slot:
                try:
                    dt = datetime.strptime(slot, "%Y-%m-%d %H:%M")
                except Exception:
                    dt = None
            # Fallback to exam_date + start_time
            if dt is None and exam_date:
                try:
                    time_part = start_time or '00:00:00'
                    if len(time_part.split(':')) == 2:
                        time_part = time_part + ':00'
                    dt = datetime.fromisoformat(f"{exam_date}T{time_part}")
                except Exception:
                    dt = None

            parsed.append((dt, b))

        # Sort by datetime (None values go last)
        parsed.sort(key=lambda x: (x[0] is None, x[0]))
        for dt, b in parsed:
            # Build display fields
            subject = b.get('subject') or ''
            child_name = b.get('child_name') or ''
            child_surname = b.get('child_surname') or b.get('child_lastname') or ''
            school = b.get('school')

            # Parent details
            parent_name = None
            parent_contact = None
            parent_email = None
            try:
                p = find_parent(b.get('parent_id'), b)
                if p:
                    parent_name = p.get('parent_name') or p.get('name') or p.get('parent')
                    parent_contact = p.get('phone') or p.get('mobile')
                    parent_email = p.get('email')
                    if not school:
                        school = p.get('school')
            except Exception:
                p = None

            # Date/time display
            date_str = ''
            time_str = ''
            if dt:
                date_str = dt.date().isoformat()
                time_str = dt.time().strftime('%H:%M')
            else:
                if exam_date:
                    date_str = exam_date
                if start_time:
                    # normalize HH:MM:SS -> HH:MM
                    try:
                        time_str = start_time.split(':')[0] + ':' + start_time.split(':')[1]
                    except Exception:
                        time_str = start_time

            # Render a clear booking row
            header = f"{date_str} {time_str} — {subject}"
            details = f"Client: {child_name} {child_surname} | School: {school or '—'}"
            parent_info = f"Parent: {parent_name or '—'} | Contact: {parent_contact or parent_email or '—'}"

            st.markdown(f"**{header}**")
            st.write(details)
            st.write(parent_info)

            # Tutor action buttons: Accept or Decline assignment
            try:
                current_status = (b.get('status') or '').strip()
                session_key = f"tutor_action_{b.get('id')}"

                # If DB already reflects an accepted/declined status, show label
                if current_status == 'TutorConfirmed' or st.session_state.get(session_key) == 'accepted':
                    st.markdown("**Status:** ✅ Accepted")
                elif current_status == 'TutorDeclined' or st.session_state.get(session_key) == 'declined':
                    st.markdown("**Status:** ❌ Declined")
                else:
                    action_cols = st.columns([1,1])
                    with action_cols[0]:
                        if st.button("✅ Accept", key=f"accept_{b.get('id')}"):
                            try:
                                # Set session flag so UI updates immediately
                                st.session_state[session_key] = 'accepted'
                                # Update booking status to indicate tutor accepted
                                supabase.table('bookings').update({"status": "TutorConfirmed"}).eq('id', b.get('id')).execute()

                                # Gather details for emails
                                tutor_name = f"{profile.get('name','')} {profile.get('surname','')}".strip()
                                tutor_contact = profile.get('phone') or profile.get('email') or 'no contact'
                                child = b.get('child_name') or b.get('student_name') or ''
                                subject = b.get('subject') or ''
                                exam_date = b.get('exam_date') or ''
                                start_time = b.get('start_time') or ''

                                # Find parent info
                                parent = find_parent(b.get('parent_id'), b) or {}
                                parent_email = parent.get('email')
                                parent_name = parent.get('parent_name') or parent.get('name') or ''
                                parent_phone = parent.get('phone') or parent.get('mobile') or ''

                                # Email configured admin/notifications address with full details (if configured)
                                try:
                                    notif_to = os.getenv('ADMIN_EMAIL') or _get_sender()
                                    if notif_to:
                                        subj = f"Tutor accepted booking: {child} — {subject}"
                                        body = (
                                            f"Tutor: {tutor_name}\n"
                                            f"Tutor contact: {tutor_contact}\n\n"
                                            f"Parent: {parent_name}\n"
                                            f"Parent email: {parent_email or 'N/A'}\n"
                                            f"Parent phone: {parent_phone or 'N/A'}\n\n"
                                            f"Child: {child}\n"
                                            f"Subject: {subject}\n"
                                            f"Date: {exam_date}\n"
                                            f"Start Time: {start_time}\n"
                                        )
                                        send_email(notif_to, subj, body)
                                except Exception:
                                    pass

                                # Email parent a confirmation with tutor contact
                                try:
                                    if parent_email:
                                        p_subj = f"Tutor confirmed for your booking — {child}"
                                        tutor_display = tutor_name or (profile.get('name') or '')
                                        p_body = (
                                            f"Hello {parent_name or ''},\n\n"
                                            f"Your booking for {child} on {exam_date} at {start_time} has been accepted by the tutor.\n"
                                            f"Subject: {subject}\n"
                                            f"Tutor: {tutor_display}\n"
                                            f"Tutor contact: {tutor_contact}\n\n"
                                            f"If you have any questions, reply to this email or contact admin.\n\nThe Turning Point"
                                        )
                                        send_email(parent_email, p_subj, p_body)
                                except Exception:
                                    pass

                                st.success("You accepted this booking. Parent and notifications team have been emailed.")
                                try:
                                    st.experimental_rerun()
                                except Exception:
                                    pass
                            except Exception as e:
                                st.error(f"Failed to accept booking: {e}")
                    with action_cols[1]:
                        if st.button("❌ Decline", key=f"decline_{b.get('id')}"):
                            try:
                                # Set session flag so UI updates immediately
                                st.session_state[session_key] = 'declined'
                                # Mark booking as declined by tutor
                                supabase.table('bookings').update({"status": "TutorDeclined"}).eq('id', b.get('id')).execute()
                                # Notify admins about the decline
                                try:
                                    admin_body = (
                                        f"Tutor {profile.get('name')} {profile.get('surname')} (id: {profile.get('id')}) has declined booking {b.get('id')}.\n"
                                        f"Child: {b.get('child_name')}\nSubject: {b.get('subject')}\nDate: {b.get('exam_date')}\nStart: {b.get('start_time')}\n"
                                    )
                                    send_admin_email(f"Tutor declined booking {b.get('id')}", admin_body)
                                except Exception:
                                    pass

                                st.info("You declined this booking — admin has been notified.")
                                try:
                                    st.experimental_rerun()
                                except Exception:
                                    pass
                            except Exception as e:
                                st.error(f"Failed to decline booking: {e}")
            except Exception:
                pass

            # Debug helper: if parent info missing, show raw booking and lookup result
            if not parent_name or not (parent_contact or parent_email):
                try:
                    with st.expander("Debug: booking / parent lookup (click to expand)"):
                        st.write("Booking record:")
                        st.json(b)
                        st.write("Parent lookup result:")
                        try:
                            p_try = find_parent(b.get('parent_id'), b)
                            st.json(p_try or {})
                        except Exception as _:
                            st.write("Parent lookup threw an error")
                except Exception:
                    pass
except Exception as e:
    st.error(f"Could not fetch bookings: {e}")
