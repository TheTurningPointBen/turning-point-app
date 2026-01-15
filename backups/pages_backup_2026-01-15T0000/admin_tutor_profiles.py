```python
import streamlit as st
st.set_page_config(page_title="Admin Tutor Profiles")
from utils.database import supabase

st.title("Tutor Profiles — Admin")

if "admin" not in st.session_state:
    st.warning("Please log in as admin on the Admin page first.")
    st.stop()

# Top-left small Back button that returns to the Admin Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_dashboard_profiles"):
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
    # select all columns to avoid failing when optional columns (email/notes) are missing
    tutors_res = supabase.table("tutors").select("*").order("name").execute()
    tutors = tutors_res.data or []
except Exception as e:
    st.error(f"Could not load tutors: {e}")
    st.stop()

# Only include tutors that are approved (confirmed in Tutor Confirmation)
confirmed = [t for t in tutors if t.get("approved")]

if not confirmed:
    st.info("No confirmed tutors found")
else:
    tutor_map = {f"{t.get('name')} {t.get('surname')} ({t.get('city') or '—'})": t.get('id') for t in confirmed}
    selected_label = st.selectbox("Select Tutor to view / edit", options=[""] + list(tutor_map.keys()))
    if selected_label:
        tutor_id = tutor_map.get(selected_label)
        try:
            t_res = supabase.table("tutors").select("*").eq("id", tutor_id).execute()
            tutor = (t_res.data or [None])[0]
        except Exception as e:
            st.error(f"Failed to load tutor: {e}")
            tutor = None

        if tutor:
            st.markdown("---")
            st.subheader(f"Edit profile: {tutor.get('name')} {tutor.get('surname')}")
            with st.form(key=f"edit_tutor_{tutor_id}"):
                name = st.text_input("First name", value=tutor.get('name') or "")
                surname = st.text_input("Surname", value=tutor.get('surname') or "")
                phone = st.text_input("Phone", value=tutor.get('phone') or "")
                email = st.text_input("Email", value=tutor.get('email') or "")
                city = st.text_input("City", value=tutor.get('city') or "")
                roles = st.text_input("Roles (Reader/Scribe/Both)", value=tutor.get('roles') or "")
                approved = st.checkbox("Approved", value=bool(tutor.get('approved')))
                notes = st.text_area("Notes", value=tutor.get('notes') or "")

                submitted = st.form_submit_button("Save changes")
                if submitted:
                    # Build payload only with keys that exist in the current tutor record
                    payload = {}
                    existing_keys = set(tutor.keys())
                    fields = {
                        "name": name,
                        "surname": surname,
                        "phone": phone,
                        "email": email,
                        "city": city,
                        "roles": roles,
                        "approved": approved,
                        "notes": notes,
                    }
                    for k, v in fields.items():
                        if k in existing_keys:
                            payload[k] = v

                    # If payload is empty, nothing to update
                    if not payload:
                        st.info("No updatable columns found for this tutor.")
                    else:
                        try:
                            upd = supabase.table("tutors").update(payload).eq("id", tutor_id).execute()
                            if getattr(upd, 'error', None) is None:
                                st.success("Tutor profile updated")
                                try:
                                    st.experimental_rerun()
                                except Exception:
                                    pass
                            else:
                                st.error(f"Update failed: {getattr(upd, 'error', upd)}")
                        except Exception as e:
                            st.error(f"Failed to update tutor: {e}")
