import streamlit as st
from utils.ui import hide_sidebar
from utils.database import supabase
from datetime import date, datetime, timedelta

hide_sidebar()

st.title("Admin Area")

if "admin" not in st.session_state:
    st.warning("Please log in as admin on the Admin page first.")
    try:
        st.switch_page("pages/admin.py")
    except Exception:
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
