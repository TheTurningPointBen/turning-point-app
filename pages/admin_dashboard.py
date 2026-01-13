import streamlit as st
from datetime import date, datetime
import math
import pandas as pd
from utils.database import supabase

st.title("Admin Dashboard")

if "admin" not in st.session_state:
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

# --- Filter controls ---
col1, col2, col3 = st.columns(3)

with col1:
    filter_date = st.date_input("Exam Date (single-day filter)", value=None)

with col2:
    filter_school = st.text_input("School")

with col3:
    # allow showing cancelled bookings
    show_cancelled = st.checkbox("Show Cancelled", value=False)

# optional tutor filter
tutor_res = supabase.table("tutors").select("id,name,surname").eq("approved", True).execute()
tutor_map = {"All": None}
for t in (tutor_res.data or []):
    tutor_map[f"{t.get('name')} {t.get('surname')}"] = t.get('id')

filter_tutor = st.selectbox("Tutor", options=list(tutor_map.keys()))

# --- Build query ---
query = supabase.table("bookings").select("*")

if filter_date:
    # bookings store exam_date as ISO string
    query = query.eq("exam_date", filter_date.isoformat())

if not show_cancelled:
    query = query.eq("cancelled", False)

if filter_school:
    query = query.ilike("school", f"%{filter_school}%")

selected_tutor_id = tutor_map.get(filter_tutor)
if selected_tutor_id:
    query = query.eq("tutor_id", selected_tutor_id)
res = query.order("start_time").execute()

if not (res.data and len(res.data)):
    st.info("No bookings found.")
else:
    # CSV export for the full result set
    try:
        df_all = pd.DataFrame(res.data)
        csv_bytes = df_all.to_csv(index=False).encode("utf-8")
        st.download_button("Export CSV (all results)", data=csv_bytes, file_name="bookings.csv", mime="text/csv")
    except Exception:
        st.info("CSV export unavailable for this result set.")

    # Pagination controls
    page_size = st.selectbox("Page size", options=[10, 25, 50, 100], index=0)
    total_items = len(res.data)
    total_pages = math.ceil(total_items / page_size)

    if "admin_dashboard_page" not in st.session_state:
        st.session_state.admin_dashboard_page = 0

    colp1, colp2, colp3 = st.columns([1, 2, 1])
    with colp1:
        if st.button("Previous"):
            if st.session_state.admin_dashboard_page > 0:
                st.session_state.admin_dashboard_page -= 1
    with colp3:
        if st.button("Next"):
            if st.session_state.admin_dashboard_page < total_pages - 1:
                st.session_state.admin_dashboard_page += 1

    st.write(f"Page {st.session_state.admin_dashboard_page + 1} of {total_pages} — {total_items} bookings")

    start_index = st.session_state.admin_dashboard_page * page_size
    end_index = start_index + page_size
    page_items = res.data[start_index:end_index]

    # Grouping behavior
    bookings = res.data

    # helper to format date as day month year
    def fmt_date(iso_date_str):
        try:
            d = datetime.fromisoformat(iso_date_str).date()
            return d.strftime("%d %b %Y")
        except Exception:
            return iso_date_str

    if group_by == "None":
        for b in page_items:
            exam_date = fmt_date(b.get("exam_date"))
            start = b.get("start_time")
            end = b.get("end_time") or ""
            header = f"{exam_date} | {b.get('school')} | {start} – {end}"

            with st.expander(header):
                st.write(f"Booking ID: {b.get('id')}")
                st.write(f"Parent ID: {b.get('parent_id')}")
                    st.write(f"Tutor ID: {b.get('tutor_id')}")
                st.write(f"Role: {b.get('role_required') or b.get('role')}")
                st.write(f"Cancelled: {'Yes' if b.get('cancelled') else 'No'}")
                st.write(f"Status: {b.get('status')}")
                st.write(f"Notes: {b.get('notes')}")

                if not b.get('cancelled'):
                    if st.button("Cancel Booking", key=f"cancel_{b.get('id')}"):
                        try:
                            cancel_time = datetime.now()
                            update_payload = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
                            supabase.table("bookings").update(update_payload).eq("id", b.get('id')).execute()

                            # compute billing window if we have date/time
                            hours_before = None
                            try:
                                if b.get('exam_date') and b.get('start_time'):
                                    exam_dt = datetime.combine(datetime.fromisoformat(b.get('exam_date')), datetime.strptime(b.get('start_time'), "%H:%M:%S").time())
                                    hours_before = (exam_dt - cancel_time).total_seconds() / 3600
                            except Exception:
                                hours_before = None

                            if hours_before is not None and hours_before < 12:
                                st.warning("Booking cancelled. Cancelled within 12 hours — billing may apply.")
                            else:
                                st.success("Booking cancelled without penalty.")

                            try:
                                st.experimental_rerun()
                            except Exception:
                                pass
                        except Exception as e:
                            st.error(f"Failed to cancel booking: {e}")
    else:
        # group by Tutor or Parent
        key_field = "tutor_id" if group_by == "Tutor" else "parent_id"
        # build map of id -> list of bookings
        groups = {}
        for b in bookings:
            k = b.get(key_field) or "Unknown"
            groups.setdefault(k, []).append(b)

        # resolve names for groups
        if group_by == "Tutor":
            ids = [k for k in groups.keys() if k != "Unknown"]
            tutor_rows = {}
            if ids:
                t_res = supabase.table("tutors").select("id,name,surname").in_("id", ids).execute()
                for t in (t_res.data or []):
                    tutor_rows[t.get('id')] = f"{t.get('name')} {t.get('surname')}"
        else:
            ids = [k for k in groups.keys() if k != "Unknown"]
            parent_rows = {}
            if ids:
                p_res = supabase.table("parents").select("id,child_name").in_("id", ids).execute()
                for p in (p_res.data or []):
                    parent_rows[p.get('id')] = p.get('child_name') or p.get('id')

        for person_id, blist in groups.items():
            label = person_id
            if person_id == "Unknown":
                label = "Unknown"
            else:
                if group_by == "Tutor":
                    label = tutor_rows.get(person_id, person_id)
                else:
                    label = parent_rows.get(person_id, person_id)

            with st.expander(f"{label} — {len(blist)} bookings"):
                for b in blist:
                    d = fmt_date(b.get('exam_date'))
                    st.write(f"{d} | {b.get('start_time')} – {b.get('end_time') or ''} | {b.get('school')} | Status: {b.get('status')}")

# --- Tutor availability overview ---
st.markdown("---")
st.subheader("Tutor Availability Overview")

tutor_res = supabase.table("tutors").select("*").eq("approved", True).execute()
for t in (tutor_res.data or []):
    with st.expander(f"{t.get('name')} {t.get('surname')}"):
        avail = supabase.table("tutor_availability").select("*").eq("tutor_id", t.get('id')).order("available_date").execute()
        if avail.data:
            for a in avail.data:
                st.write(f"{a.get('available_date')} | {a.get('start_time')} – {a.get('end_time')}")
        else:
            st.write("No availability")

    # --- Period selection: billing month or custom range ---
    period_choice = st.radio("Period", options=["Billing Month", "Custom Range"], horizontal=True)
    if period_choice == "Billing Month":
        today = date.today()
        # if day <=25, billing period is 26 of previous month -> 25 of current month
        if today.day <= 25:
            # previous month
            if today.month == 1:
                prev_month = 12
                prev_year = today.year - 1
            else:
                prev_month = today.month - 1
                prev_year = today.year
            start_period = date(prev_year, prev_month, 26)
            end_period = date(today.year, today.month, 25)
        else:
            # day >25: billing period is 26 of current month -> 25 of next month
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year
            start_period = date(today.year, today.month, 26)
            end_period = date(next_year, next_month, 25)
        st.write(f"Billing period: {start_period.strftime('%d %b %Y')} → {end_period.strftime('%d %b %Y')}")
    else:
        start_period = st.date_input("Start date", value=None)
        end_period = st.date_input("End date", value=None)

    # Grouping: show bookings per Tutor or Parent
    group_by = st.selectbox("Group bookings by", options=["None", "Tutor", "Parent"], index=1)
