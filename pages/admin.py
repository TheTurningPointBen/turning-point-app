import streamlit as st
from utils.ui import hide_sidebar

# Apply global hide-sidebar config for consistent layout
hide_sidebar()
from datetime import datetime, timedelta
from utils.database import supabase
from utils.email import send_email, send_admin_email
from utils.session import restore_session_from_refresh, set_auth_user_password

# If a one-time refresh token was pushed into the URL (tp_rt), try restoring session
try:
    params = st.query_params or {}
except Exception:
    params = {}

if params.get('tp_rt'):
    token = params.get('tp_rt')[0]
    restored = None
    try:
        restored = restore_session_from_refresh(token)
    except Exception:
        restored = None

    if restored and restored.get('user'):
        st.session_state['authenticated'] = True
        st.session_state['user'] = restored.get('user')
        st.session_state['role'] = 'admin'
        st.session_state['email'] = restored.get('user', {}).get('email')
        try:
            st.experimental_set_query_params()
        except Exception:
            pass
        try:
            st.experimental_rerun()
        except Exception:
            try:
                st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
            except Exception:
                pass

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

tab1 = st.tabs(["Login"])[0]

with tab1:
    st.subheader("Admin Login")
    # Prefill email from localStorage if present (client-side)
    st.markdown(
        """
        <script>
        (function(){
            try{
                const v = localStorage.getItem('tp_email_admin');
                if(v){
                    const labels = Array.from(document.querySelectorAll('label'));
                    for(const l of labels){
                        if(l.innerText && l.innerText.trim()==='Admin Email'){
                            const input = l.parentElement.querySelector('input') || l.nextElementSibling || l.parentElement.nextElementSibling.querySelector('input');
                            if(input){ input.value = v; input.dispatchEvent(new Event('input',{bubbles:true})); break; }
                        }
                    }
                }
            }catch(e){}
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

    admin_email = st.text_input("Admin Email", key="admin_login_email")
    remember = st.checkbox("Remember me", key="remember_admin")
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
                # Save email to localStorage if user opted in
                if remember:
                    import json
                    st.markdown(f"<script>localStorage.setItem('tp_email_admin', {json.dumps(admin_email)});</script>", unsafe_allow_html=True)
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
                    from utils.session import generate_recovery_link
                    from utils.email import send_email
                    import os

                    site = os.getenv('SITE_URL') or os.getenv('APP_URL') or 'http://localhost:8501'
                    gen = generate_recovery_link(fp_email, redirect_to=site + '/password_reset')
                    if gen.get('ok'):
                        raw_link = gen.get('direct_link') or gen.get('link')
                        try:
                            from urllib.parse import urlparse, parse_qs
                            p = urlparse(raw_link)
                            token = None
                            q = parse_qs(p.query)
                            if 'access_token' in q:
                                token = q.get('access_token')[0]
                            if not token and p.fragment:
                                fq = parse_qs(p.fragment)
                                if 'access_token' in fq:
                                    token = fq.get('access_token')[0]
                        except Exception:
                            token = None

                        if token:
                            link = site.rstrip('/') + f"/password_reset?type=recovery&access_token={token}"
                        else:
                            link = raw_link

                        subj = 'Turning Point — Password reset instructions'
                        plain = f"Follow this link to reset your password: {link}\nIf you did not request this, ignore this email."
                        html = f"<p>Follow this link to reset your password:</p><p><a href=\"{link}\">Reset password</a></p>"
                        send_res = send_email(fp_email, subj, body=plain, html=html)
                        if send_res.get('ok'):
                            st.success('If that email exists, password reset instructions have been sent.')
                        else:
                            st.warning('Password reset request could not be sent — please contact support.')
                    else:
                        st.warning('Password reset request could not be sent — please contact support.')
                except Exception as e:
                    st.error("Failed to request password reset. Please try again later.")
                    try:
                        st.exception(e)
                    except Exception:
                        pass

# Registration disabled for admins — admin users must be created internally.

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    # Authentication required — stop rendering further admin content.
    st.stop()

# --- ADMIN PASSWORD RESET TOOL ---
with st.expander("Reset parent/tutor password (admin)"):
    st.write("Use this tool to set a new password for a parent or tutor account via the Supabase Admin API.")
    pr_role = st.selectbox("Role", ["Parent", "Tutor"], help="Which user table to lookup")
    pr_email = st.text_input("Account email", key="admin_reset_email")
    pr_pw = st.text_input("New password", type="password", key="admin_reset_pw")
    pr_pw2 = st.text_input("Confirm new password", type="password", key="admin_reset_pw2")
    if st.button("Reset password", key="admin_reset_submit"):
        if not pr_email:
            st.error("Please enter an account email.")
        elif not pr_pw or pr_pw != pr_pw2:
            st.error("Passwords must match and not be empty.")
        else:
            try:
                # Lookup user_id from the appropriate table
                tbl = 'parents' if pr_role == 'Parent' else 'tutors'
                q = supabase.table(tbl).select('user_id,email').eq('email', pr_email).execute()
                rows = getattr(q, 'data', None) or []
                user_id = None
                if rows and len(rows) > 0:
                    user_id = rows[0].get('user_id')

                if not user_id:
                    st.error('Could not find a linked auth user_id for that email. Ensure the account exists and is linked to the parents/tutors table.')
                else:
                    res = set_auth_user_password(user_id, pr_pw)
                    if res.get('ok'):
                        st.success('Password updated successfully.')
                    else:
                        st.error(f"Failed to update password: {res}")
            except Exception as e:
                st.error('Exception while resetting password; see details below.')
                try:
                    st.exception(e)
                except Exception:
                    pass

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
            'afr': 'afrikaans',
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

    # determine language column and exam date object
    lang_col = _language_column_for(booking.get('subject'))
    try:
        exam_date_obj = datetime.fromisoformat(booking.get('exam_date')).date() if booking.get('exam_date') else None
    except Exception:
        exam_date_obj = None

    for tutor in (tutors_res.data or []):
        # role match
        if not role_matches(tutor.get('roles'), booking.get('role_required')):
            continue
        # language match: only enforce if the tutor has any explicit
        # language flags. Tutors with no language ticks are assumed able
        # to cover any language subject.
        def _tutor_has_any_lang_flags(t_row):
            return any(bool(t_row.get(k)) for k in ('afrikaans', 'isizulu', 'setswana', 'isixhosa', 'french'))

        if lang_col and _tutor_has_any_lang_flags(tutor) and not tutor.get(lang_col):
            continue
        # availability check (only if we have valid parsed start_time and exam_date)
        if start_time and exam_date_obj:
            if not _tutor_is_available(tutor.get('id'), exam_date_obj, start_time, booking.get('duration') or 60):
                continue
        suitable_tutors.append(tutor)

    # Show all suitable tutors (no arbitrary limit)

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
                else:
                    st.warning("Tutor lookup failed — tutor contact not found.")

                # fetch parent email (fallback to booking row if parents record missing)
                p_res = supabase.table('parents').select('email').eq('id', booking.get('parent_id')).execute()
                parent_email = (p_res.data or [None])[0].get('email') if getattr(p_res, 'data', None) else None
                if not parent_email:
                    # try booking-level fields
                    parent_email = (booking.get('parent_email') or booking.get('email') or None)
                if not parent_email:
                    st.warning("Parent email not found — parent may not have been notified")

                parent_sent = False
                tutor_sent = False
                tutor_email = None
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
                    else:
                        parent_sent = True
                    # Also notify the tutor if we have their email
                        try:
                            tutor_email = t.get('email') if getattr(t_res, 'data', None) else None
                            if tutor_email:
                                tutor_body = [
                                    f"You have been assigned a booking.",
                                    f"Child: {booking.get('child_name')}",
                                    f"Subject: {booking.get('subject')}",
                                    f"Date: {booking.get('exam_date')}",
                                    f"Start: {booking.get('start_time')}",
                                ]
                                if tutor_name:
                                    tutor_body.append(f"Tutor: {tutor_name}")
                                if tutor_contact:
                                    tutor_body.append(f"Contact: {tutor_contact}")
                                tutor_body.append("\nPlease confirm your availability.\n\nThe Turning Point")
                                send_tutor = send_email(tutor_email, "New Booking Assigned", "\n".join(tutor_body))
                                if send_tutor.get('error'):
                                    st.warning(f"Failed to send assignment email to tutor: {send_tutor.get('error')}")
                                else:
                                    tutor_sent = True
                        except Exception:
                            pass

                # Notify admin of email send status
                recipients = []
                if parent_sent and parent_email:
                    recipients.append(parent_email)
                if tutor_sent and tutor_email:
                    recipients.append(tutor_email)
                if recipients:
                    st.success(f"Notification email(s) sent to: {', '.join(recipients)}")
                # Send admin a summary email about what was sent
                try:
                    subject = f"Booking {booking.get('id')} - notification summary"
                    body_lines = [
                        f"Booking ID: {booking.get('id')}",
                        f"Child: {booking.get('child_name')}",
                        f"Subject: {booking.get('subject')}",
                        f"Date: {booking.get('exam_date')}",
                        f"Assigned tutor id: {tutor_id}",
                        "",
                        f"Parent email sent: {parent_sent} ({parent_email})",
                        f"Tutor email sent: {tutor_sent} ({tutor_email})",
                    ]
                    admin_notify = send_admin_email(subject, "\n".join(body_lines))
                    if admin_notify.get('error'):
                        st.warning(f"Failed to send admin notification email: {admin_notify.get('error')}")
                    else:
                        st.info("Admin notified by email about sent notifications.")
                except Exception:
                    pass
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
