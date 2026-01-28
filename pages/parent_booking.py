import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Parent Booking")
except Exception:
    pass
from datetime import datetime, timedelta, time
from utils.database import supabase
from utils.email import send_admin_email

if "user" not in st.session_state:
    st.error("Please log in first")
    st.stop()

# Get parent profile
user = st.session_state["user"]
profile_res = supabase.table("parents").select("*").eq("user_id", user.id).execute()
profile = profile_res.data[0]

# Determine children for this parent (support multiple children)
children = profile.get('children') or []
if not children:
    first = profile.get('child_name') or profile.get('child_firstname') or None
    if first:
        children = [{'name': first, 'grade': profile.get('grade'), 'school': profile.get('school')}]

child_options = []
for c in (children or []):
    n = c.get('name') or 'Unnamed'
    g = c.get('grade') or ''
    s = c.get('school') or ''
    label = f"{n}"
    if g:
        label += f" — Grade {g}"
    if s:
        label += f" | {s}"
    child_options.append({'label': label, 'data': c})

# If multiple children, let parent choose which child this booking is for
selected_child = None
if child_options:
    labels = [c['label'] for c in child_options]
    idx = st.selectbox("Which child is this for?", options=list(range(len(labels))), format_func=lambda i: labels[i])
    selected_child = child_options[idx]['data']
    # Provide quick link to edit/add children in profile
    col_edit, _ = st.columns([1, 3])
    with col_edit:
        if st.button("Add / Edit children"):
            try:
                # set profile edit mode and open profile page
                st.session_state['editing_profile'] = True
                try:
                    st.switch_page('pages/parent_profile.py')
                except Exception:
                    st.session_state['page'] = 'parent_profile'
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass
            except Exception:
                pass
else:
    selected_child = None

# Top-left Back button (smaller) and header inline
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_profile"):
        try:
            st.switch_page("pages/parent_dashboard.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass

    # Small inline styling for the Back button (applies after render)
    st.markdown(
        """
        <style>
        /* Minimal spacer to keep layout consistent */
        .parent-booking-back-space{height:4px}
        </style>
        <div class="parent-booking-back-space"></div>
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

with main_col:
    st.header("Book a Reader / Scribe for your child")

# Form inputs
# Default exam date to tomorrow (cannot pick past dates/times)
subject = st.text_input("Subject")
# Default exam date to tomorrow (cannot pick past dates/times)
# Default exam date to tomorrow (cannot pick past dates/times)
tomorrow = (datetime.now() + timedelta(days=1)).date()
today = datetime.now().date()
exam_date = st.date_input("Exam Date", value=tomorrow, min_value=today)
# Default start time remains 07:45
start_time = st.time_input("Start Time", value=time(7, 45))
duration = st.number_input("Duration (minutes)", min_value=30, max_value=180, value=60)
extra_time = st.number_input("Extra Time (minutes)", min_value=0, max_value=60, value=0)
role_options = ["Reader", "Scribe", "Both (Reader & Scribe)", "Invigilator", "Prompter", "All of the Above"]
role_required = st.selectbox("Role Required", role_options)

# Show tutors who are approved and match the required role and language/availability
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

def _tutor_is_available(tutor_id, exam_date, start_time_obj, duration_minutes):
    try:
        # find any unavailability entries that cover the exam date
        u_res = supabase.table('tutor_unavailability').select('*').eq('tutor_id', tutor_id).lte('start_date', exam_date.isoformat()).gte('end_date', exam_date.isoformat()).execute()
        entries = u_res.data or []
        if not entries:
            return True
        # booking time
        from datetime import datetime, time
        b_start = start_time_obj
        # compute booking end time
        bhour, bmin = b_start.hour, b_start.minute
        import datetime as _dt
        bstart_dt = _dt.datetime.combine(exam_date, b_start)
        bend_dt = bstart_dt + _dt.timedelta(minutes=duration_minutes)

        for e in entries:
            # if times are not specified, tutor is unavailable for full day
            if not e.get('start_time') or not e.get('end_time'):
                return False
            # parse times
            try:
                es = _dt.datetime.strptime(e.get('start_time'), '%H:%M:%S').time()
                ee = _dt.datetime.strptime(e.get('end_time'), '%H:%M:%S').time()
            except Exception:
                return False
            estart_dt = _dt.datetime.combine(exam_date, es)
            eend_dt = _dt.datetime.combine(exam_date, ee)
            # if time ranges overlap => unavailable
            latest_start = max(bstart_dt, estart_dt)
            earliest_end = min(bend_dt, eend_dt)
            overlap = (earliest_end - latest_start).total_seconds()
            if overlap > 0:
                return False
        return True
    except Exception:
        # On error, be conservative and mark unavailable
        return False

try:
    tutors_res = supabase.table("tutors").select("*").eq("approved", True).execute()
    all_tutors = tutors_res.data or []

    lang_col = _language_column_for(subject)

    eligible_tutors = []
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

    for t in all_tutors:
        # role match
        if not role_matches(t.get('roles'), role_required):
            continue
        # language match (if applicable)
        if lang_col:
            if not t.get(lang_col):
                continue
        # availability check
        if not _tutor_is_available(t.get('id'), exam_date, start_time, duration):
            continue
        eligible_tutors.append(t)

except Exception as e:
    st.error(f"Could not load tutors: {e}")

# Booking rules
booking_dt = datetime.combine(exam_date, start_time)
now = datetime.now()

if booking_dt < now:
    st.error("Cannot book for a past time.")
    st.stop()

# time delta between requested booking and now
delta = booking_dt - now

# Business rule: bookings within 24 hours must be made via WhatsApp
# Compute booking date/time values used later and leave tutor assignment to admin.
booking_date = exam_date
start_dt = datetime.combine(booking_date, start_time)
end_dt = start_dt + timedelta(minutes=(duration + extra_time))
selected_tutor_id = None

if booking_dt < now + timedelta(hours=24):
    wa_number_display = "+27 82 883 6167"
    wa_link = "https://wa.me/27828836167"
    st.error(f"Bookings within 24 hours must be made via WhatsApp: {wa_number_display}")
    st.markdown(f"[Open WhatsApp chat →]({wa_link})")
    st.stop()

col1, col2 = st.columns([1,1])


def _insert_booking(add_another=False):
    if delta.total_seconds() < 24*3600:
        wa_number_display = "+27 82 883 6167"
        wa_link = "https://wa.me/27828836167"
        st.warning(f"You can still submit, but admin will require WhatsApp confirmation via {wa_number_display}.")
        st.markdown(f"[Open WhatsApp chat →]({wa_link})")

    # Use selected child details if available
    child_name = None
    grade_val = None
    school_val = None
    if selected_child:
        child_name = selected_child.get('name')
        grade_val = selected_child.get('grade')
        school_val = selected_child.get('school')
    else:
        child_name = profile.get('child_name')
        grade_val = profile.get('grade')
        school_val = profile.get('school')

    insert_res = supabase.table("bookings").insert({
        "parent_id": profile["id"],
        "child_name": child_name,
        "grade": grade_val,
        "school": school_val,
        "subject": subject,
        "role_required": role_required,
        "exam_date": exam_date.isoformat(),
        "start_time": start_time.strftime("%H:%M:%S"),
        "duration": duration,
        "extra_time": extra_time,
        "tutor_id": selected_tutor_id
    }).execute()

    if getattr(insert_res, 'error', None) is None and insert_res.data:
        st.success("Booking submitted! Admin will confirm your tutor.")

        # Notify admin if SMTP is configured
        subject_line = f"New booking: {child_name or 'Unknown child'} — {subject}"
        body = (
            f"Parent: {user.email}\n"
            f"Child: {child_name}\n"
            f"Grade: {grade_val}\n"
            f"School: {school_val}\n"
            f"Subject: {subject}\n"
            f"Role Required: {role_required}\n"
            f"Exam Date: {exam_date.isoformat()}\n"
            f"Start Time: {start_time.strftime('%H:%M:%S')}\n"
            f"Duration: {duration} min\n"
            f"Extra Time: {extra_time} min\n"
        )
        # Notify admin about the new booking. Use explicit admin address.
        email_res = send_admin_email(subject_line, body)

        # We only notify admin on initial booking submission.
        # Admin will assign/confirm the tutor and then the app will send
        # confirmation emails to the parent and the tutor.
        st.info("Booking created. No tutor selected; admin will assign one.")
    else:
        st.error(f"Booking failed: {getattr(insert_res, 'error', None)}")


_do_save = col1.button("💾  Save Booking")
_do_save_add = col2.button("➕  Save & Add Another")

if _do_save:
    _insert_booking(add_another=False)

if _do_save_add:
    _insert_booking(add_another=True)
    try:
        st.experimental_rerun()
    except Exception:
        pass

# Note: Back/Logout button removed per user request

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
