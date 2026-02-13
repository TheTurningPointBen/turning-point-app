import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from datetime import datetime, timedelta
from utils.database import supabase


def find_tutor(tutor_ref, booking=None):
    """Try several strategies to find a tutor record for the given reference.
    tutor_ref may be an id, email, or other identifier. booking is optional and
    may contain name fields to help matching.
    Returns tutor dict or None.
    """
    if not tutor_ref:
        return None

    # Try common identifier columns
    keys_to_try = ["id", "tutor_id", "user_id", "email"]
    for k in keys_to_try:
        try:
            res = supabase.table('tutors').select('name,surname,phone,email,id').eq(k, tutor_ref).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    # Fallback: fetch all tutors and try to match in Python by id or by name
    try:
        all_res = supabase.table('tutors').select('id,name,surname,phone,email').execute()
        tutors = all_res.data or []
    except Exception:
        tutors = []

    # Try matching by id string
    for t in tutors:
        if str(t.get('id')) == str(tutor_ref):
            return t

    # Try matching by name fields present in booking
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

st.title("Confirmed Bookings — Admin")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

# Top-left small Back button that returns to the Admin Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_dashboard_confirmed"):
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

try:
    # Show bookings from now (today) up to the next 7 days
    today = datetime.now().date()
    end_date = (datetime.now() + timedelta(days=7)).date()
    # Consider several statuses that represent a confirmed booking from the
    # admin perspective so tutor-confirmed or assigned bookings are included.
    statuses = ["Confirmed", "TutorConfirmed", "Assigned"]
    bookings_res = supabase.table("bookings").select("*").in_("status", statuses).gte('exam_date', today.isoformat()).lte('exam_date', end_date.isoformat()).order("exam_date").execute()
    bookings = bookings_res.data or []
except Exception as e:
    st.error(f"Could not load confirmed bookings: {e}")
    st.stop()

# Filter out bookings that have already passed
from datetime import datetime
now = datetime.now()
filtered = []
for b in bookings:
    try:
        date_str = b.get('exam_date')
        time_str = b.get('start_time') or '00:00:00'
        dt = datetime.combine(datetime.fromisoformat(date_str), datetime.strptime(time_str, "%H:%M:%S").time())
    except Exception:
        # If we can't parse the datetime, keep the booking to avoid accidental hiding
        filtered.append(b)
        continue
    if dt >= now:
        filtered.append(b)

bookings = filtered

if not bookings:
    st.info("No upcoming confirmed bookings")
    st.stop()

for b in bookings:
    st.divider()
    # Header with inline cancel icon
    cols = st.columns([9,1])
    with cols[0]:
        st.subheader(f"{b.get('child_name')} — {b.get('subject')}")
        st.write(f"Date: {b.get('exam_date')} | Start: {b.get('start_time')}")
    with cols[1]:
        if st.button("❌", key=f"cancel_icon_{b.get('id')}"):
            try:
                now = datetime.now()
                existing = set(b.keys() or [])
                candidate = {"cancelled": True, "cancelled_at": now.isoformat(), "status": "Cancelled"}
                payload = {k: v for k, v in candidate.items() if k in existing}
                if not payload:
                    cols[1].error("Unable to cancel: bookings table missing cancel/status columns. Cancel manually in DB.")
                else:
                    supabase.table('bookings').update(payload).eq('id', b.get('id')).execute()
                    # show confirmation across the row (left column) instead of below
                    cols[0].success("Booking cancelled")
            except Exception as e:
                cols[1].error(f"Failed to cancel booking: {e}")

    # Tutor details: show full name + phone (never show raw tutor id)
    tutor_display = "Tutor: not assigned"
    if b.get('tutor_id'):
        try:
            t = find_tutor(b.get('tutor_id'), b)
            if t:
                tutor_display = f"Tutor: {t.get('name','')} {t.get('surname','')} — {t.get('phone') or t.get('email') or 'no contact'}"
            else:
                tutor_display = "Tutor: (lookup failed)"
        except Exception:
            tutor_display = "Tutor: (lookup failed)"

    st.write(tutor_display)

    # Parent notification status (based on confirmed_at and parent email)
    parent_email = None
    try:
        p_res = supabase.table('parents').select('id,email').eq('id', b.get('parent_id')).execute()
        p = (p_res.data or [None])[0]
        if p and p.get('email'):
            parent_email = p.get('email')
    except Exception:
        parent_email = None

    confirmed_at = b.get('confirmed_at') if 'confirmed_at' in (b.keys() or []) else None
    if parent_email and confirmed_at:
        st.success(f"Parent notified: {parent_email}")
    elif parent_email:
        st.info(f"Parent email: {parent_email} — notification may not have been sent")
    else:
        st.warning("Parent email not found — parent may not have been notified")
