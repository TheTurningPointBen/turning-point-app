import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
st.set_page_config(page_title="Parent Your Bookings")
from utils.database import supabase


def _find_tutor_record(tutor_ref):
    """Robust tutor lookup: try direct id match, then fall back to scanning tutors and matching by id string."""
    if not tutor_ref:
        return None
    try:
        # select all columns to avoid errors when some columns (e.g. email) don't exist
        res = supabase.table("tutors").select("*").eq("id", tutor_ref).execute()
        if getattr(res, 'data', None):
            return res.data[0]
    except Exception:
        pass
    try:
        all_res = supabase.table("tutors").select("*").execute()
        tutors = all_res.data or []
    except Exception:
        tutors = []
    for t in tutors:
        if str(t.get('id')) == str(tutor_ref):
            return t
    return None

# Toggle to show debug info on tutor lookup failures
DEBUG_TUTOR_LOOKUP = True

if "user" not in st.session_state:
    st.info("Please log in first via the Parent Portal.")
else:
    user = st.session_state["user"]
    profile_res = supabase.table("parents").select("*").eq("user_id", user.id).execute()
    profile = profile_res.data[0] if profile_res.data else None

    if not profile:
        st.warning("No parent profile found. Please create your profile first.")
        if st.button("Create Profile"):
            try:
                st.switch_page("pages/parent_profile.py")
            except Exception:
                st.experimental_rerun()
    else:
        # Small Back button (returns to Parent Dashboard)
        back_col, main_col = st.columns([1, 9])
        with back_col:
            if st.button("⬅️ Back", key="back_to_dashboard_bookings"):
                try:
                    st.switch_page("pages/parent_dashboard.py")
                except Exception:
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass

            st.markdown(
                """
                <style>
                .parent-back-space{height:4px}
                </style>
                <div class="parent-back-space"></div>
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

        st.title("Your Bookings")

        try:
            bookings_res = supabase.table("bookings").select("*").eq("parent_id", profile.get("id")).in_("status", ["Pending", "Confirmed"]).order("exam_date", desc=False).execute()
            bookings = bookings_res.data or []
        except Exception as e:
            st.error(f"Could not load bookings: {e}")
            bookings = []

        if not bookings:
            st.info("No bookings found. You can make a booking now.")
            if st.button("Make a Booking"):
                try:
                    st.switch_page("pages/parent_booking.py")
                except Exception:
                    st.experimental_rerun()
        else:
            # Partition bookings into pending and confirmed
            pending = [bb for bb in bookings if (bb.get('status') or '').lower() == 'pending']
            confirmed = [bb for bb in bookings if (bb.get('status') or '').lower() == 'confirmed']

            # Pending bookings section
            st.header("Pending Bookings")
            if not pending:
                st.info("You have no pending bookings.")
            else:
                for b in pending:
                    exam_date = b.get("exam_date")
                    start_time = b.get("start_time")
                    subject = b.get("subject") or "(no subject)"

                    display_date = exam_date
                    try:
                        from datetime import datetime
                        display_date = datetime.fromisoformat(exam_date).date().isoformat()
                    except Exception:
                        pass

                    display_time = start_time
                    try:
                        from datetime import datetime
                        display_time = datetime.strptime(start_time, "%H:%M:%S").time().strftime("%H:%M")
                    except Exception:
                        pass

                    line = f"{display_date} {display_time} — {subject} (Pending)"
                    cols = st.columns([9, 1])
                    with cols[0]:
                        st.write(line)
                    with cols[1]:
                        cancel_key = f"cancel_{b.get('id')}"
                        if st.button("❌", key=cancel_key):
                            from datetime import datetime, timedelta, time as dt_time

                            cancel_time = datetime.now()
                            exam_date_raw = b.get("exam_date")
                            start_time_raw = b.get("start_time")
                            cutoff_applies = False
                            try:
                                exam_date_obj = datetime.fromisoformat(exam_date_raw).date()
                                start_time_obj = datetime.strptime(start_time_raw, "%H:%M:%S").time()
                                exam_dt = datetime.combine(exam_date_obj, start_time_obj)

                                cutoff = datetime.combine(exam_dt.date() - timedelta(days=1), dt_time(17, 0))
                                if cancel_time > cutoff:
                                    cutoff_applies = True
                            except Exception:
                                cutoff_applies = False

                            try:
                                existing = set(b.keys() or [])
                                candidate = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
                                payload = {k: v for k, v in candidate.items() if k in existing}

                                if not payload:
                                    st.error("Unable to cancel: bookings table missing cancel/status columns. Cancel manually in DB.")
                                else:
                                    supabase.table("bookings").update(payload).eq("id", b.get("id")).execute()

                                    if cutoff_applies:
                                        wa_number_display = "+27 82 883 6167"
                                        wa_link = "https://wa.me/27828836167"
                                        st.warning(f"Cancelled after 17:00 the day before — billing may apply. For emergencies after this cutoff please call or WhatsApp {wa_number_display}.")
                                        st.markdown(f"[Open WhatsApp →]({wa_link})")
                                    else:
                                        st.success("Booking cancelled without penalty.")

                                    try:
                                        st.experimental_rerun()
                                    except Exception:
                                        pass
                            except Exception as e:
                                st.error(f"Failed to cancel booking: {e}")

                # Hide non-parent pages from the sidebar for logged-in parents
                if st.session_state.get("role") == "parent" or "user" in st.session_state:
                    st.markdown(
                        """
                        <script>
                        (function(){
                            const allowed = ['Parent','Parent Portal','Parent Dashboard','Parent Profile','Parent Booking','Parent Your Bookings','Your Bookings','Profile','Bookings','Booking'];
                            const hideNonParent = ()=>{
                                try{
                                    const sidebar = document.querySelector('aside');
                                    if(!sidebar) return;
                                    const links = sidebar.querySelectorAll('a');
                                    links.forEach(a=>{
                                        const txt = (a.innerText||a.textContent||'').trim();
                                        const keep = allowed.some(k=> txt.indexOf(k)!==-1);
                                        if(!keep){
                                            const node = a.closest('div');
                                            if(node) node.style.display='none';
                                        }
                                    });
                                }catch(e){}
                            };
                            setTimeout(hideNonParent, 200);
                        })();
                        </script>
                        """,
                        unsafe_allow_html=True,
                    )

            # Confirmed bookings section
            st.header("Confirmed Bookings")
            if not confirmed:
                st.info("You have no confirmed bookings.")
            else:
                for b in confirmed:
                    exam_date = b.get("exam_date")
                    start_time = b.get("start_time")
                    subject = b.get("subject") or "(no subject)"

                    display_date = exam_date
                    try:
                        from datetime import datetime
                        display_date = datetime.fromisoformat(exam_date).date().isoformat()
                    except Exception:
                        pass

                    display_time = start_time
                    try:
                        from datetime import datetime
                        display_time = datetime.strptime(start_time, "%H:%M:%S").time().strftime("%H:%M")
                    except Exception:
                        pass

                    line = f"{display_date} {display_time} — {subject} (Booked)"

                    # Tutor lookup (existing logic)
                    tutor_id = b.get("tutor_id")
                    if tutor_id:
                        try:
                            t = _find_tutor_record(tutor_id)
                            if t:
                                tutor_name = f"{t.get('name','')} {t.get('surname','')}".strip()
                                contact = t.get("phone") or t.get("email") or "no contact"
                                line = f"{line} — Tutor: {tutor_name} — {contact}"
                            else:
                                # Stronger fallback: fetch all tutors and compare stringified ids
                                try:
                                    all_res = supabase.table("tutors").select("*").execute()
                                    tutors = all_res.data or []
                                except Exception:
                                    tutors = []
                                found = None
                                for tt in tutors:
                                    if str(tt.get('id')) == str(tutor_id) or (tt.get('id') and str(tutor_id) in str(tt.get('id'))):
                                        found = tt
                                        break
                                if found:
                                    tutor_name = f"{found.get('name','')} {found.get('surname','')}".strip()
                                    contact = found.get('phone') or found.get('email') or 'no contact'
                                    line = f"{line} — Tutor: {tutor_name} — {contact}"
                                    # optionally show debug info when lookup succeeds (useful during testing)
                                    if DEBUG_TUTOR_LOOKUP:
                                        with st.expander(f"Tutor lookup (booking {b.get('id')})", expanded=False):
                                            st.write("tutor_id", tutor_id)
                                            st.write("matched_record", found)
                                else:
                                    line = f"{line} — Tutor assigned (id: {tutor_id})"
                                    if DEBUG_TUTOR_LOOKUP:
                                        with st.expander(f"Tutor lookup failed (booking {b.get('id')})", expanded=True):
                                            st.write("tutor_id", tutor_id)
                                            try:
                                                direct = supabase.table("tutors").select("*").eq("id", tutor_id).execute()
                                                st.write("direct query result", getattr(direct, 'data', None))
                                            except Exception as e:
                                                st.write("direct query exception", str(e))
                                            try:
                                                sample = supabase.table("tutors").select("*").limit(50).execute()
                                                st.write("sample tutors (first 50)", getattr(sample, 'data', None))
                                            except Exception as e:
                                                st.write("sample query exception", str(e))
                        except Exception:
                            pass

                    cols = st.columns([9, 1])
                    with cols[0]:
                        st.write(line)
                    with cols[1]:
                        cancel_key = f"cancel_{b.get('id')}"
                        if st.button("❌", key=cancel_key):
                            from datetime import datetime, timedelta, time as dt_time

                            cancel_time = datetime.now()
                            exam_date_raw = b.get("exam_date")
                            start_time_raw = b.get("start_time")
                            cutoff_applies = False
                            try:
                                exam_date_obj = datetime.fromisoformat(exam_date_raw).date()
                                start_time_obj = datetime.strptime(start_time_raw, "%H:%M:%S").time()
                                exam_dt = datetime.combine(exam_date_obj, start_time_obj)

                                cutoff = datetime.combine(exam_dt.date() - timedelta(days=1), dt_time(17, 0))
                                if cancel_time > cutoff:
                                    cutoff_applies = True
                            except Exception:
                                cutoff_applies = False

                            try:
                                existing = set(b.keys() or [])
                                candidate = {"cancelled": True, "cancelled_at": cancel_time.isoformat(), "status": "Cancelled"}
                                payload = {k: v for k, v in candidate.items() if k in existing}

                                if not payload:
                                    st.error("Unable to cancel: bookings table missing cancel/status columns. Cancel manually in DB.")
                                else:
                                    supabase.table("bookings").update(payload).eq("id", b.get("id")).execute()

                                    if cutoff_applies:
                                        wa_number_display = "+27 82 883 6167"
                                        wa_link = "https://wa.me/27828836167"
                                        st.warning(f"Cancelled after 17:00 the day before — billing may apply. For emergencies after this cutoff please call or WhatsApp {wa_number_display}.")
                                        st.markdown(f"[Open WhatsApp →]({wa_link})")
                                    else:
                                        st.success("Booking cancelled without penalty.")

                                    try:
                                        st.experimental_rerun()
                                    except Exception:
                                        pass
                            except Exception as e:
                                st.error(f"Failed to cancel booking: {e}")
