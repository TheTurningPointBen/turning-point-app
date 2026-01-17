import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Tutor Unavailability")
except Exception:
    pass
from datetime import date
from utils.database import supabase

st.title("Tutor Unavailability")

if "user" not in st.session_state:
    st.info("Please log in first.")
    st.stop()

user = st.session_state["user"]

# fetch tutor profile
profile_res = supabase.table("tutors").select("*").eq("user_id", user.id).execute()
profile = profile_res.data[0] if profile_res.data else None

if not profile:
    st.warning("Please complete your tutor profile first.")
    st.stop()

if not profile.get("approved"):
    st.warning("Your tutor profile is pending approval.")
    st.stop()

# Top-left Back button to return to Tutor Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_tutor_dashboard_unavailability"):
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

st.subheader("Mark when you are UNAVAILABLE")

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)

# Add availability
start_date = st.date_input("Start date (first day you're unavailable)", min_value=date.today())
end_date = st.date_input("End date (last day you're unavailable)", min_value=start_date)

with st.expander("Optional: restrict to times of day"):
    specify_times = st.checkbox("This unavailability is only for specific times each day")
    if specify_times:
        start_time = st.time_input("Unavailable from (time)")
        end_time = st.time_input("Unavailable until (time)")
    else:
        start_time = None
        end_time = None

reason = st.text_input("Reason (optional)")

if st.button("Add Unavailability"):
    if specify_times and start_time and end_time and start_time >= end_time:
        st.error("End time must be after start time.")
    else:
        insert_payload = {
            "tutor_id": profile["id"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "reason": reason
        }
        if specify_times and start_time and end_time:
            insert_payload.update({
                "start_time": start_time.strftime("%H:%M:%S"),
                "end_time": end_time.strftime("%H:%M:%S")
            })

        insert_res = supabase.table("tutor_unavailability").insert(insert_payload).execute()

        if getattr(insert_res, 'error', None) is None:
            st.success("Unavailability added.")
            safe_rerun()
        else:
            st.error(getattr(insert_res, 'error', None))

# Show existing unavailability
unavail_res = supabase.table("tutor_unavailability") \
    .select("*") \
    .eq("tutor_id", profile["id"]) \
    .order("start_date") \
    .execute()

if unavail_res.data:
    for a in unavail_res.data:
        times = "(full day)"
        if a.get('start_time') and a.get('end_time'):
            times = f"{a.get('start_time')} – {a.get('end_time')}"
        st.write(f"{a.get('start_date')} → {a.get('end_date')} {times} — {a.get('reason')}")
        if st.button("Remove", key=f"remove_unavail_{a.get('id')}"):
            supabase.table("tutor_unavailability").delete().eq("id", a.get('id')).execute()
            st.success("Removed")
            safe_rerun()
else:
    st.info("No unavailability entries yet. By default you are considered available unless you add an unavailability.")

