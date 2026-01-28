import streamlit as st
from utils.ui import hide_sidebar
from utils.database import supabase
from utils.email import send_admin_email
from datetime import date, datetime, time, timedelta

hide_sidebar()

st.title("Admin Area")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

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
            if lang_col and not t.get(lang_col):
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
                ins = supabase.table('bookings').insert({
                    'parent_id': selected_parent.get('id'),
                    'child_name': child_name,
                    'grade': grade_val,
                    'school': school_val,
                    'subject': subject,
                    'role_required': role_required,
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
                else:
                    st.error(f"Failed to create booking: {getattr(ins, 'error', None)}")
            except Exception as e:
                st.error(f"Failed to create booking: {e}")

        if st.button("Save Manual Booking", key="admin_manual_save"):
            _admin_insert_booking()
