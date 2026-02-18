import os
import streamlit as st
from utils.ui import hide_sidebar
from utils.database import supabase
from utils.email import send_admin_email, send_email, _get_sender
from utils.session import delete_auth_user, set_auth_user_password, get_supabase_service, get_supabase
from datetime import date, datetime, time, timedelta
import json
import base64
import requests

hide_sidebar()

st.title("Admin Area")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

# Non-secret indicator: show whether SUPABASE_SERVICE_ROLE is configured
_svc_present = bool(os.getenv('SUPABASE_SERVICE_ROLE'))
if _svc_present:
    st.info('SUPABASE_SERVICE_ROLE: configured (service operations enabled)')
else:
    st.warning('SUPABASE_SERVICE_ROLE: not configured — admin service operations disabled')

# Mailblaze debug: check HTTP connectivity and send test messages
with st.expander('Mailblaze Debug'):
    base_default = os.getenv('MAILBLAZE_BASE') or os.getenv('MAILBLAZE_BASE_URL') or os.getenv('mailblaze_http') or 'https://control.mailblaze.com/api'
    mb_key = (
        os.getenv('MAILBLAZE_API_KEY')
        or os.getenv('MAILBLAZE_KEY')
        or os.getenv('mailblaze_api_key')
        or os.getenv('MAILBLAZE_APIKEY')
    )

    st.write('Mailblaze API key present:', bool(mb_key))

    if st.button('Check Mailblaze connectivity'):
        if not base_default:
            st.error('Missing Mailblaze base URL (MAILBLAZE_BASE or mailblaze_http)')
        else:
            st.info(f'Attempting HTTPS GET to {base_default} (5s timeout)')
            try:
                headers = {"Authorization": f"Bearer {mb_key}"} if mb_key else {}
                r = requests.get(base_default, headers=headers, timeout=5)
                st.write(f'Status: {r.status_code}')
                if r.status_code < 400:
                    st.success('Connectivity to Mailblaze base URL succeeded')
                else:
                    st.error(f'Connectivity test returned status {r.status_code}')
            except Exception as e:
                st.error(f'Connectivity check failed: {e}')

    # Mailblaze send test
    try:
        default_from = _get_sender() or os.getenv('SMTP_USER')
        # Default test recipient set to ben@youthrive.co.za per admin request.
        # Preserve explicit user edits across the Streamlit session, but if the
        # session key is missing (first load) initialise it to the desired default.
        default_recipient = os.getenv('MB_TEST_RECIPIENT', 'ben@youthrive.co.za')
        if 'mb_test_recipient' not in st.session_state:
            st.session_state['mb_test_recipient'] = default_recipient
        mb_recipient = st.text_input('Mailblaze test recipient', value=st.session_state.get('mb_test_recipient'), key='mb_test_recipient')
        mb_subject = st.text_input('Mailblaze test subject', value='Turning Point — Mailblaze test', key='mb_test_subject')
        mb_body = st.text_area('Mailblaze test body (plain text)', value='This is a Mailblaze test email from Turning Point Admin.', key='mb_test_body')
        if st.button('Send test via Mailblaze', key='mb_send_test'):
            if not mb_key:
                st.error('MAILBLAZE_API_KEY (or mailblaze_api_key) is not set in environment')
            elif not default_from:
                st.error('SENDER_EMAIL or EMAIL_FROM is not configured')
            else:
                try:
                    encoded_body = base64.b64encode(mb_body.encode("utf-8")).decode("utf-8")
                except Exception:
                    encoded_body = mb_body

                payload = {
                    "to_email": mb_recipient,
                    "to_name": None,
                    "from_email": default_from,
                    "from_name": os.getenv('MAILBLAZE_FROM_NAME') or os.getenv('EMAIL_FROM_NAME') or None,
                    "subject": mb_subject,
                    "body": encoded_body,
                    "plain_text": encoded_body,
                }

                headers = {"Authorization": f"Bearer {mb_key}", "Content-Type": "application/x-www-form-urlencoded"}
                base = os.getenv('MAILBLAZE_BASE') or os.getenv('MAILBLAZE_BASE_URL') or os.getenv('mailblaze_http') or 'https://control.mailblaze.com/api'
                endpoints = [f"{base.rstrip('/')}/transactional"]
                results = []
                for ep in endpoints:
                    try:
                        r = requests.post(ep, data=payload, headers=headers, timeout=10)
                        results.append((ep, r.status_code, r.text))
                        if r.status_code in (200, 201, 202):
                            st.success(f'Mailblaze test send accepted via {ep}')
                            break
                    except Exception as e:
                        results.append((ep, 'err', repr(e)))
                st.write('Results:')
                for ep, status, body in results:
                    try:
                        st.text(f'{ep} → {status} — {body}')
                    except Exception:
                        st.write(f'{ep} → {status}')
    except Exception:
        pass

    # (SendGrid test removed)

# Top-left small Back button that returns to the Admin Dashboard
back_col1, back_col2 = st.columns([1, 8])
with back_col1:
    if st.button("← Back", key="admin_admin_area_back"):
        try:
            st.switch_page("pages/admin_dashboard.py")
        except Exception:
            try:
                st.session_state.admin_dashboard_view = "area"
                st.experimental_rerun()
            except Exception:
                pass
with back_col2:
    pass

st.markdown("---")
st.write("Welcome to the Admin Area. Use the buttons below to manage tutors, bookings and settings.")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Tutor Profiles"):
        try:
            st.switch_page("pages/admin_tutor_profiles.py")
        except Exception:
            pass
with col2:
    if st.button("Tutors"):
        try:
            st.switch_page("pages/admin_tutors.py")
        except Exception:
            pass
with col3:
    pass

st.markdown("---")

# Billing / Invoices / Download tools
cb1, cb2, cb3 = st.columns(3)
with cb1:
    with st.expander("Client Billing"):
        st.write("Select a client to view bookings for billing.")

        # Fetch clients (parents)
        try:
            p_res = supabase.table("parents").select("id,parent_name,phone").order("parent_name").execute()
            parents = p_res.data or []
        except Exception as e:
            st.error(f"Failed to fetch clients: {e}")
            parents = []

        if not parents:
            st.warning("No clients found.")
        else:
            # Build select options mapping
            options = []
            id_map = {}
            for p in parents:
                display = p.get("parent_name") or p.get("phone") or str(p.get("id"))
                label = f"{display} — {p.get('phone') or ''}".strip()
                options.append(label)
                id_map[label] = p.get("id")

            selected_label = st.selectbox("Client", options, key="client_billing_select")
            selected_parent_id = id_map.get(selected_label)

            mode = st.radio("Show bookings for:", ["Billing period", "Custom date range"], index=0, key="client_billing_mode")

            def fetch_bookings_for_parent(parent_id, start_iso, end_iso):
                try:
                    q = supabase.table("bookings").select("*")
                    # Only include confirmed bookings for billing
                    q = q.eq("parent_id", parent_id).eq("status", "Confirmed").gte("exam_date", start_iso).lte("exam_date", end_iso).order("exam_date")
                    r = q.execute()
                    return r.data or []
                except Exception as e:
                    st.error(f"Failed to fetch bookings: {e}")
                    return []

            if mode == "Billing period":
                today = date.today()

                # Billing period runs 26th -> 25th of the following month.
                # If today is on/after the 26th, the period starts on the 26th of this month
                # and ends on the 25th of the next month. Otherwise it starts on the 26th
                # of the previous month and ends on the 25th of this month.
                if today.day >= 26:
                    start = today.replace(day=26)
                    if start.month == 12:
                        end = date(start.year + 1, 1, 25)
                    else:
                        end = date(start.year, start.month + 1, 25)
                else:
                    if today.month == 1:
                        start = date(today.year - 1, 12, 26)
                    else:
                        start = date(today.year, today.month - 1, 26)
                    end = date(today.year, today.month, 25)

                start_iso = start.isoformat()
                end_iso = end.isoformat()

                st.write(f"Billing period: {start_iso} → {end_iso}")
                if st.button("Show bookings for billing period", key="show_billing_period"):
                    bookings = fetch_bookings_for_parent(selected_parent_id, start_iso, end_iso)
                    if not bookings:
                        st.info("No bookings found for this billing period.")
                    else:
                        try:
                            import pandas as pd

                            # Enrich bookings with parent and tutor names
                            parent_ids = list({b.get('parent_id') for b in bookings if b.get('parent_id')})
                            tutor_ids = list({b.get('tutor_id') for b in bookings if b.get('tutor_id')})

                            parent_map = {}
                            if parent_ids:
                                try:
                                    pres = supabase.table('parents').select('id,parent_name').in_('id', parent_ids).execute()
                                    for p in (pres.data or []):
                                        parent_map[p.get('id')] = p.get('parent_name')
                                except Exception:
                                    parent_map = {}

                            tutor_map = {}
                            if tutor_ids:
                                try:
                                    tres = supabase.table('tutors').select('id,name,surname').in_('id', tutor_ids).execute()
                                    for t in (tres.data or []):
                                        name = (t.get('name') or '')
                                        surname = (t.get('surname') or '')
                                        tutor_map[t.get('id')] = f"{name} {surname}".strip()
                                except Exception:
                                    tutor_map = {}

                            for b in bookings:
                                b['parent_name'] = parent_map.get(b.get('parent_id')) or b.get('parent_id')
                                b['tutor_name'] = tutor_map.get(b.get('tutor_id')) or b.get('tutor_id')

                            # Build minimal export rows with requested columns
                            rows = []
                            for b in bookings:
                                rows.append({
                                    "Parent Name": b.get('parent_name') or b.get('parent_id'),
                                    "Child Name": b.get('child_name') or '',
                                    "Exam Date": b.get('exam_date') or '',
                                    "Duration": b.get('duration') or '',
                                    "Tutor Name": b.get('tutor_name') or b.get('tutor_id'),
                                    "Confirmed": (b.get('status') == 'Confirmed')
                                })

                            df = pd.DataFrame(rows)
                            st.dataframe(df)
                            csv = df.to_csv(index=False)
                            st.download_button("Download CSV", csv, file_name=f"bookings_{selected_parent_id}_{start_iso}_{end_iso}.csv", mime="text/csv")
                        except Exception as e:
                            st.error(f"Failed to display bookings: {e}")

            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    start_d = st.date_input("Start date", value=(date.today() - timedelta(days=30)), key="client_billing_start")
                with col_b:
                    end_d = st.date_input("End date", value=date.today(), key="client_billing_end")

                if st.button("Show bookings for range", key="show_custom_range"):
                    if start_d > end_d:
                        st.error("Start date must be before end date.")
                    else:
                        start_iso = start_d.isoformat()
                        end_iso = end_d.isoformat()
                        bookings = fetch_bookings_for_parent(selected_parent_id, start_iso, end_iso)
                        if not bookings:
                            st.info("No bookings found for this date range.")
                        else:
                            try:
                                import pandas as pd

                                # Enrich bookings with parent/tutor names then show minimal columns
                                parent_ids = list({b.get('parent_id') for b in bookings if b.get('parent_id')})
                                tutor_ids = list({b.get('tutor_id') for b in bookings if b.get('tutor_id')})

                                parent_map = {}
                                if parent_ids:
                                    try:
                                        pres = supabase.table('parents').select('id,parent_name').in_('id', parent_ids).execute()
                                        for p in (pres.data or []):
                                            parent_map[p.get('id')] = p.get('parent_name')
                                    except Exception:
                                        parent_map = {}

                                tutor_map = {}
                                if tutor_ids:
                                    try:
                                        tres = supabase.table('tutors').select('id,name,surname').in_('id', tutor_ids).execute()
                                        for t in (tres.data or []):
                                            name = (t.get('name') or '')
                                            surname = (t.get('surname') or '')
                                            tutor_map[t.get('id')] = f"{name} {surname}".strip()
                                    except Exception:
                                        tutor_map = {}

                                rows = []
                                for b in bookings:
                                    rows.append({
                                        "Parent Name": parent_map.get(b.get('parent_id')) or b.get('parent_id'),
                                        "Child Name": b.get('child_name') or '',
                                        "Exam Date": b.get('exam_date') or '',
                                        "Duration": b.get('duration') or '',
                                        "Tutor Name": tutor_map.get(b.get('tutor_id')) or b.get('tutor_id'),
                                        "Confirmed": (b.get('status') == 'Confirmed')
                                    })

                                df = pd.DataFrame(rows)
                                st.dataframe(df)
                                csv = df.to_csv(index=False)
                                st.download_button("Download CSV", csv, file_name=f"bookings_{selected_parent_id}_{start_iso}_{end_iso}.csv", mime="text/csv")
                            except Exception as e:
                                st.error(f"Failed to display bookings: {e}")
with cb2:
    with st.expander("Tutor Invoices"):
        st.write("Select a tutor to view bookings for billing.")

        # Fetch tutors
        try:
            t_res = supabase.table('tutors').select('id,name,surname').order('name').execute()
            tutors = t_res.data or []
        except Exception as e:
            st.error(f"Failed to fetch tutors: {e}")
            tutors = []

        if not tutors:
            st.warning("No tutors found.")
        else:
            options = []
            tutor_id_map = {}
            for t in tutors:
                label = f"{(t.get('name') or '')} {(t.get('surname') or '')}".strip()
                if not label:
                    label = t.get('id')
                options.append(label)
                tutor_id_map[label] = t.get('id')

            selected_label = st.selectbox("Tutor", options, key="tutor_billing_select")
            selected_tutor_id = tutor_id_map.get(selected_label)

            mode = st.radio("Show bookings for:", ["Billing period", "Custom date range"], index=0, key="tutor_billing_mode")

            def fetch_bookings_for_tutor(tutor_id, start_iso, end_iso):
                try:
                    q = supabase.table('bookings').select('*')
                    q = q.eq('tutor_id', tutor_id).eq('status', 'Confirmed').gte('exam_date', start_iso).lte('exam_date', end_iso).order('exam_date')
                    r = q.execute()
                    return r.data or []
                except Exception as e:
                    st.error(f"Failed to fetch bookings: {e}")
                    return []

            if mode == "Billing period":
                today = date.today()

                if today.day >= 26:
                    start = today.replace(day=26)
                    if start.month == 12:
                        end = date(start.year + 1, 1, 25)
                    else:
                        end = date(start.year, start.month + 1, 25)
                else:
                    if today.month == 1:
                        start = date(today.year - 1, 12, 26)
                    else:
                        start = date(today.year, today.month - 1, 26)
                    end = date(today.year, today.month, 25)

                start_iso = start.isoformat()
                end_iso = end.isoformat()

                st.write(f"Billing period: {start_iso} → {end_iso}")
                if st.button("Show bookings for billing period", key="show_tutor_billing_period"):
                    bookings = fetch_bookings_for_tutor(selected_tutor_id, start_iso, end_iso)
                    if not bookings:
                        st.info("No bookings found for this billing period.")
                    else:
                        try:
                            import pandas as pd

                            # Enrich bookings with parent names
                            parent_ids = list({b.get('parent_id') for b in bookings if b.get('parent_id')})
                            parent_map = {}
                            if parent_ids:
                                try:
                                    pres = supabase.table('parents').select('id,parent_name').in_('id', parent_ids).execute()
                                    for p in (pres.data or []):
                                        parent_map[p.get('id')] = p.get('parent_name')
                                except Exception:
                                    parent_map = {}

                            rows = []
                            for b in bookings:
                                rows.append({
                                    "Parent Name": parent_map.get(b.get('parent_id')) or b.get('parent_id'),
                                    "Child Name": b.get('child_name') or '',
                                    "Exam Date": b.get('exam_date') or '',
                                    "Duration": b.get('duration') or '',
                                    "Tutor Name": selected_label,
                                    "Confirmed": True,
                                })

                            df = pd.DataFrame(rows)
                            st.dataframe(df)
                            csv = df.to_csv(index=False)
                            st.download_button("Download CSV", csv, file_name=f"tutor_{selected_tutor_id}_{start_iso}_{end_iso}.csv", mime="text/csv")
                        except Exception as e:
                            st.error(f"Failed to display bookings: {e}")
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    start_d = st.date_input("Start date", value=(date.today() - timedelta(days=30)), key="tutor_billing_start")
                with col_b:
                    end_d = st.date_input("End date", value=date.today(), key="tutor_billing_end")

                if st.button("Show bookings for range", key="show_tutor_custom_range"):
                    if start_d > end_d:
                        st.error("Start date must be before end date.")
                    else:
                        start_iso = start_d.isoformat()
                        end_iso = end_d.isoformat()
                        bookings = fetch_bookings_for_tutor(selected_tutor_id, start_iso, end_iso)
                        if not bookings:
                            st.info("No bookings found for this date range.")
                        else:
                            try:
                                import pandas as pd

                                # Enrich bookings with parent names
                                parent_ids = list({b.get('parent_id') for b in bookings if b.get('parent_id')})
                                parent_map = {}
                                if parent_ids:
                                    try:
                                        pres = supabase.table('parents').select('id,parent_name').in_('id', parent_ids).execute()
                                        for p in (pres.data or []):
                                            parent_map[p.get('id')] = p.get('parent_name')
                                    except Exception:
                                        parent_map = {}

                                rows = []
                                for b in bookings:
                                    rows.append({
                                        "Parent Name": parent_map.get(b.get('parent_id')) or b.get('parent_id'),
                                        "Child Name": b.get('child_name') or '',
                                        "Exam Date": b.get('exam_date') or '',
                                        "Duration": b.get('duration') or '',
                                        "Tutor Name": selected_label,
                                        "Confirmed": True,
                                    })

                                df = pd.DataFrame(rows)
                                st.dataframe(df)
                                csv = df.to_csv(index=False)
                                st.download_button("Download CSV", csv, file_name=f"tutor_{selected_tutor_id}_{start_iso}_{end_iso}.csv", mime="text/csv")
                            except Exception as e:
                                st.error(f"Failed to display bookings: {e}")
with cb3:
    if st.button("Download"):
        st.info("Preparing bookings CSV...")
        try:
            res = supabase.table('bookings').select('*').execute()
            data = res.data or []
        except Exception as e:
            st.error(f"Failed to fetch bookings: {e}")
            data = []

        if not data:
            st.warning("No bookings found to download.")
        else:
            try:
                import pandas as pd

                bookings = data

                # Enrich with parent and tutor names
                parent_ids = list({b.get('parent_id') for b in bookings if b.get('parent_id')})
                tutor_ids = list({b.get('tutor_id') for b in bookings if b.get('tutor_id')})

                parent_map = {}
                if parent_ids:
                    try:
                        pres = supabase.table('parents').select('id,parent_name').in_('id', parent_ids).execute()
                        for p in (pres.data or []):
                            parent_map[p.get('id')] = p.get('parent_name')
                    except Exception:
                        parent_map = {}

                tutor_map = {}
                if tutor_ids:
                    try:
                        tres = supabase.table('tutors').select('id,name,surname').in_('id', tutor_ids).execute()
                        for t in (tres.data or []):
                            name = (t.get('name') or '')
                            surname = (t.get('surname') or '')
                            tutor_map[t.get('id')] = f"{name} {surname}".strip()
                    except Exception:
                        tutor_map = {}

                for b in bookings:
                    b['parent_name'] = parent_map.get(b.get('parent_id')) or b.get('parent_id')
                    b['tutor_name'] = tutor_map.get(b.get('tutor_id')) or b.get('tutor_id')

                # Build minimal export rows with requested columns
                rows = []
                for b in bookings:
                    rows.append({
                        "Parent Name": b.get('parent_name') or b.get('parent_id'),
                        "Child Name": b.get('child_name') or '',
                        "Exam Date": b.get('exam_date') or '',
                        "Duration": b.get('duration') or '',
                        "Tutor Name": b.get('tutor_name') or b.get('tutor_id'),
                        "Confirmed": (b.get('status') == 'Confirmed')
                    })

                df = pd.DataFrame(rows)
                csv = df.to_csv(index=False)
                st.download_button("Download bookings CSV", csv, file_name="bookings.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Failed to prepare CSV: {e}")


# -- Manual booking: allow admin to create a booking for a client --
with st.expander("Create Manual Booking (Admin)"):
    st.write("Create a booking on behalf of a client.")

    # Fetch parents
    try:
        pres = supabase.table("parents").select("*").order("parent_name").execute()
        parents = pres.data or []
    except Exception as e:
        st.error(f"Failed to load clients: {e}")
        parents = []

    if not parents:
        st.warning("No clients found.")
    else:
        opts = []
        pid_map = {}
        for p in parents:
            display = p.get('parent_name') or p.get('phone') or str(p.get('id'))
            label = f"{display} — {p.get('phone') or ''}".strip()
            opts.append(label)
            pid_map[label] = p

        sel_label = st.selectbox("Client", opts, key="admin_manual_client_select")
        selected_parent = pid_map.get(sel_label)

        # Children for this parent
        children = selected_parent.get('children') or []
        if not children:
            first = selected_parent.get('child_name') or selected_parent.get('child_firstname') or None
            if first:
                children = [{'name': first, 'grade': selected_parent.get('grade'), 'school': selected_parent.get('school')}]

        child_label = None
        selected_child = None
        if children:
            labels = []
            for c in children:
                n = c.get('name') or 'Unnamed'
                g = c.get('grade') or ''
                s = c.get('school') or ''
                lbl = n
                if g:
                    lbl += f" — Grade {g}"
                if s:
                    lbl += f" | {s}"
                labels.append(lbl)
            idx = st.selectbox("Which child is this for?", options=list(range(len(labels))), format_func=lambda i: labels[i], key="admin_manual_child_select")
            selected_child = children[idx]

        # Booking inputs
        subject = st.text_input("Subject", key="admin_manual_subject")
        today = datetime.now().date()
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        exam_date = st.date_input("Exam Date", value=tomorrow, min_value=today, key="admin_manual_exam_date")
        start_time = st.time_input("Start Time", value=time(7, 45), key="admin_manual_start_time")
        duration = st.number_input("Duration (minutes)", min_value=30, max_value=480, value=60, key="admin_manual_duration")
        extra_time = st.number_input("Extra Time (minutes)", min_value=0, max_value=120, value=0, key="admin_manual_extra_time")
        role_options = ["Reader", "Scribe", "Both (Reader & Scribe)", "Invigilator", "Prompter", "All of the Above"]
        role_required = st.selectbox("Role Required", role_options, key="admin_manual_role")

        # Tutor selection (optional)
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

        # fetch tutors with full data to allow filtering
        try:
            tres = supabase.table('tutors').select('*').eq('approved', True).order('name').execute()
            tutors = tres.data or []
        except Exception:
            tutors = []

        # normalize roles stored labels
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

        tutor_opts = ["Unassigned"]
        tutor_map = {"Unassigned": None}

        lang_col = _language_column_for(subject)
        exam_date_obj = exam_date if exam_date else None

        for t in tutors:
            if not role_matches(t.get('roles'), role_required):
                continue
            # Tutors who have no explicit language ticks are assumed able to cover
            # language subjects; only enforce the language requirement if the
            # tutor has any language flags set and doesn't include the required one.
            def _tutor_has_any_lang_flags(tutor_row):
                return any(bool(tutor_row.get(k)) for k in ('afrikaans', 'isizulu', 'setswana', 'isixhosa', 'french'))

            if lang_col and _tutor_has_any_lang_flags(t) and not t.get(lang_col):
                continue
            if exam_date_obj and start_time:
                if not _tutor_is_available(t.get('id'), exam_date_obj, start_time, duration):
                    continue
            label = f"{(t.get('name') or '')} {(t.get('surname') or '')}".strip() or str(t.get('id'))
            tutor_opts.append(label)
            tutor_map[label] = t.get('id')

        selected_tutor_label = st.selectbox("Assign Tutor (optional)", tutor_opts, key="admin_manual_tutor")
        selected_tutor_id = tutor_map.get(selected_tutor_label)

        status = st.selectbox("Booking status", ["Pending", "Confirmed"], index=0, key="admin_manual_status")

        def _admin_insert_booking():
            booking_dt = datetime.combine(exam_date, start_time)
            now = datetime.now()
            if booking_dt < now:
                st.error("Cannot create a booking in the past.")
                return

            # Prepare child details
            child_name = None
            grade_val = None
            school_val = None
            if selected_child:
                child_name = selected_child.get('name')
                grade_val = selected_child.get('grade')
                school_val = selected_child.get('school')
            else:
                child_name = selected_parent.get('child_name')
                grade_val = selected_parent.get('grade')
                school_val = selected_parent.get('school')

            try:
                # Normalize role label to DB-acceptable value (strip human-friendly extras)
                db_role_required = role_required
                try:
                    if role_required:
                        rr = str(role_required)
                        if "Both" in rr:
                            db_role_required = "Both"
                        elif "Reader" in rr and "Scribe" in rr:
                            db_role_required = "Both"
                        elif "Reader" in rr:
                            db_role_required = "Reader"
                        elif "Scribe" in rr:
                            db_role_required = "Scribe"
                        elif "Invigilator" in rr:
                            db_role_required = "Invigilator"
                        elif "Prompter" in rr:
                            db_role_required = "Prompter"
                        elif "All" in rr:
                            db_role_required = "All of the Above"
                except Exception:
                    db_role_required = role_required

                ins = supabase.table('bookings').insert({
                    'parent_id': selected_parent.get('id'),
                    'child_name': child_name,
                    'grade': grade_val,
                    'school': school_val,
                    'subject': subject,
                    'role_required': db_role_required,
                    'exam_date': exam_date.isoformat(),
                    'start_time': start_time.strftime('%H:%M:%S'),
                    'duration': int(duration),
                    'extra_time': int(extra_time),
                    'tutor_id': selected_tutor_id,
                    'status': status,
                }).execute()

                if getattr(ins, 'error', None) is None and ins.data:
                    st.success('Manual booking created.')
                    # Notify admin and optionally parent
                    sub = f"Manual booking created: {child_name or 'Child'} — {subject}"
                    body = (
                        f"Admin created booking for parent id {selected_parent.get('id')}\n"
                        f"Child: {child_name}\n"
                        f"Exam Date: {exam_date.isoformat()} {start_time.strftime('%H:%M:%S')}\n"
                        f"Duration: {duration} min (+{extra_time} extra)\n"
                        f"Tutor assigned: {selected_tutor_label or 'Unassigned'}\n"
                        f"Status: {status}\n"
                    )
                    try:
                        send_admin_email(sub, body)
                    except Exception:
                        pass
                    # If booking is immediately Confirmed and a tutor was assigned, notify tutor and parent
                    try:
                        if status == 'Confirmed' and selected_tutor_id:
                            # fetch tutor
                            t_res = supabase.table('tutors').select('name,surname,email,phone').eq('id', selected_tutor_id).execute()
                            t = (t_res.data or [None])[0] if getattr(t_res, 'data', None) else None

                            # fetch parent
                            p_res = supabase.table('parents').select('parent_name,email,phone').eq('id', selected_parent.get('id')).execute()
                            p = (p_res.data or [None])[0] if getattr(p_res, 'data', None) else None

                            # notify tutor
                            try:
                                if t and t.get('email'):
                                    tutor_name = f"{t.get('name') or ''} {t.get('surname') or ''}".strip()
                                    tutor_email = t.get('email')
                                    subject_t = f"New booking assigned: {child_name or 'Child'} — {subject}"
                                    body_t = (
                                        f"Hello {tutor_name or 'Tutor'},\n\n"
                                        f"You have been assigned to a booking:\n"
                                        f"Child: {child_name}\n"
                                        f"Subject: {subject}\n"
                                        f"Date: {exam_date.isoformat()}\n"
                                        f"Start Time: {start_time.strftime('%H:%M:%S')}\n"
                                        f"Duration: {duration} minutes\n\n"
                                        f"Please log in to the admin panel to view details.\n"
                                    )
                                    send_email(tutor_email, subject_t, body_t)
                            except Exception:
                                pass

                            # notify parent
                            try:
                                if p and p.get('email'):
                                    parent_email = p.get('email')
                                    tutor_display = (f"{t.get('name') or ''} {t.get('surname') or ''}".strip()) if t else str(selected_tutor_id)
                                    subject_p = f"Booking confirmed — Tutor assigned: {tutor_display}"
                                    body_p = (
                                        f"Hello {p.get('parent_name') or ''},\n\n"
                                        f"Your booking for {child_name or ''} on {exam_date.isoformat()} at {start_time.strftime('%H:%M:%S')} has been confirmed.\n"
                                        f"Assigned tutor: {tutor_display}\n"
                                        f"Tutor email: {t.get('email') if t else 'N/A'}\n"
                                        f"Tutor phone: {t.get('phone') if t else 'N/A'}\n\n"
                                        f"If you have any questions, reply to this email or contact admin.\n"
                                    )
                                    send_email(parent_email, subject_p, body_p)
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    st.error(f"Failed to create booking: {getattr(ins, 'error', None)}")
            except Exception as e:
                st.error(f"Failed to create booking: {e}")

        if st.button("Save Manual Booking", key="admin_manual_save"):
            _admin_insert_booking()


# -- Manage Parents: allow admin to set temporary passwords or delete linked auth users --
with st.expander("Manage Parents"):
    try:
        pres = supabase.table('parents').select('*').order('parent_name').execute()
        parents = pres.data or []
    except Exception as e:
        st.error(f"Failed to load parents: {e}")
        parents = []

    if not parents:
        st.info('No parents found.')
    else:
        import secrets, string
        for p in parents:
            with st.expander(f"{p.get('parent_name') or p.get('id')}"):
                st.write(f"📞 {p.get('phone')}")
                st.write(f"📧 {p.get('email')}")
                st.write(f"Children: {p.get('children') or p.get('child_name') or ''}")

                user_id = p.get('user_id')
                if user_id:
                    delete_flag = f'confirm_delete_parent_auth_{p.get("id")}'
                    setpw_flag = f'confirm_set_parent_pw_{p.get("id")}'

                    if st.button('Delete linked Auth user', key=f'delete_parent_auth_{p.get("id")}'):
                        st.session_state[delete_flag] = True

                    if st.session_state.get(delete_flag):
                        confirm = st.text_input('Type DELETE to confirm deletion', key=f'del_input_parent_{p.get("id")}')
                        colc, cola = st.columns([1, 3])
                        with colc:
                            if confirm == 'DELETE' and st.button('Confirm delete', key=f'confirm_delete_parent_auth_confirm_{p.get("id")}'):
                                res = delete_auth_user(user_id)
                                # audit
                                try:
                                    svc = get_supabase_service()
                                    svc.table('admin_actions').insert({
                                        'admin_email': st.session_state.get('email'),
                                        'action': 'delete_auth_user',
                                        'target_type': 'parent',
                                        'target_id': str(p.get('id')),
                                        'details': {'user_id': user_id}
                                    }).execute()
                                except Exception:
                                    pass
                                st.session_state.pop(delete_flag, None)
                                if res.get('ok'):
                                    st.success('Supabase Auth user deleted.')
                                    try:
                                        st.experimental_rerun()
                                    except Exception:
                                        pass
                                else:
                                    st.error(f"Failed to delete auth user: {res.get('error')}")
                                try:
                                    send_admin_email('Admin action: delete auth user', f"Admin {st.session_state.get('email')} deleted auth user {user_id} for parent {p.get('id')}")
                                except Exception:
                                    pass
                        with cola:
                            if st.button('Cancel', key=f'confirm_delete_parent_auth_cancel_{p.get("id")}'):
                                st.session_state.pop(delete_flag, None)

                    if st.button('Set temporary password and email parent', key=f'set_parent_pw_{p.get("id")}'):
                        st.session_state[setpw_flag] = True

                    if st.session_state.get(setpw_flag):
                        st.info('A temporary password will be generated and emailed to the parent.')
                        colx, coly = st.columns([1, 3])
                        with colx:
                            if st.button('Confirm set password', key=f'confirm_set_parent_pw_confirm_{p.get("id")}'):
                                parent_email = p.get('email')
                                st.session_state.pop(setpw_flag, None)
                                if not parent_email:
                                    st.error('Parent has no email on file; cannot email temporary password.')
                                else:
                                    alphabet = string.ascii_letters + string.digits
                                    temp_pw = ''.join(secrets.choice(alphabet) for _ in range(12))
                                    resp = set_auth_user_password(user_id, temp_pw)
                                    if resp.get('ok'):
                                        subject = 'Your temporary password'
                                        body = f"Hello {p.get('parent_name') or ''},\n\nAn administrator has set a temporary password for your account.\n\nTemporary password: {temp_pw}\n\nPlease log in and change your password immediately.\n\nIf you did not request this, contact the admin.\n"
                                        mail = send_email(parent_email, subject, body)
                                        if mail.get('ok'):
                                            # audit & notify
                                            try:
                                                svc = get_supabase_service()
                                                svc.table('admin_actions').insert({
                                                    'admin_email': st.session_state.get('email'),
                                                    'action': 'set_temporary_password',
                                                    'target_type': 'parent',
                                                    'target_id': str(p.get('id')),
                                                    'details': {'user_id': user_id}
                                                }).execute()
                                            except Exception:
                                                pass
                                            try:
                                                send_admin_email('Admin action: set temporary password', f"Admin {st.session_state.get('email')} set temporary password for parent {p.get('id')}")
                                            except Exception:
                                                pass
                                            st.success('Temporary password set and emailed to the parent.')
                                            try:
                                                st.experimental_rerun()
                                            except Exception:
                                                pass
                                        else:
                                            st.warning('Password set but failed to send email to parent. See details.')
                                            st.write(mail.get('error'))
                                    else:
                                        st.error(f"Failed to set password: {resp.get('error')}")
                        with coly:
                            if st.button('Cancel', key=f'confirm_set_parent_pw_cancel_{p.get("id")}'):
                                st.session_state.pop(setpw_flag, None)

# Recent admin actions (audit)
with st.expander("Recent Admin Actions"):
    actions = []
    try:
        try:
            svc = get_supabase_service()
        except Exception:
            # Service role not configured; try public/anon client for read-only access
            st.info('Service role not configured; attempting public client for read-only admin actions.')
            svc = get_supabase()

        a_res = svc.table('admin_actions').select('*').order('created_at', desc=True).limit(50).execute()
        actions = a_res.data or []
    except Exception as e:
        # Provide a helpful message if the admin_actions table doesn't exist (PGRST205)
        msg = None
        try:
            if getattr(e, 'args', None):
                msg = e.args[0]
        except Exception:
            msg = str(e)

        if isinstance(msg, dict) and msg.get('code') == 'PGRST205':
            st.info('No admin_actions table found. Run the SQL migration scripts/add_admin_actions_table.sql in the Supabase SQL editor.')
        elif isinstance(msg, str) and 'Could not find the table' in msg:
            st.info('No admin_actions table found. Run the SQL migration scripts/add_admin_actions_table.sql in the Supabase SQL editor.')
        else:
            st.error(f'Failed to load admin actions: {e}')

        actions = []

    if not actions:
        st.info('No admin actions found.')
    else:
        rows = []
        for a in actions:
            rows.append({
                'When': a.get('created_at'),
                'Admin': a.get('admin_email'),
                'Action': a.get('action'),
                'Target': f"{a.get('target_type') or ''}:{a.get('target_id') or ''}",
                'Details': a.get('details')
            })
        try:
            import pandas as pd
            df = pd.DataFrame(rows)
            st.dataframe(df)
        except Exception:
            st.write(rows)
