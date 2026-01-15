```python
import streamlit as st
st.set_page_config(page_title="Admin Pending Bookings")
from datetime import datetime
from utils.database import supabase

st.title("Pending Bookings — Admin")

if "admin" not in st.session_state:
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
        for t in (tutors_res.data or []):
            roles = t.get("roles")
            if roles == "Both" or booking.get("role_required") in roles:
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

```