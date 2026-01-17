import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from utils.database import supabase

st.title("Tutor Profiles — Admin")

if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
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
# Show unconfirmed tutors (need admin confirmation)
unconfirmed = [t for t in tutors if not t.get("approved")]

st.header("Unconfirmed Tutor Profiles")
if not unconfirmed:
    st.info("No tutor profiles awaiting confirmation")
else:
    for t in unconfirmed:
        tid = t.get('id')
        name = f"{t.get('name') or ''} {t.get('surname') or ''}".strip()
        with st.container():
            cols = st.columns([8,2])
            with cols[0]:
                st.subheader(name or '(no name)')
                st.write(f"Email: {t.get('email') or '(no email)'} | Phone: {t.get('phone') or '(no phone)'}")
                st.write(f"City: {t.get('city') or '(no city)'} | Roles: {t.get('roles') or '(none)'}")
                if t.get('notes'):
                    st.write(f"Notes: {t.get('notes')}")
            with cols[1]:
                if st.button("Confirm", key=f"confirm_{tid}"):
                    try:
                        # attempt to set approved=True (DB may or may not include the column)
                        supabase.table('tutors').update({"approved": True}).eq('id', tid).execute()
                        st.success(f"Confirmed {name}")
                        try:
                            st.experimental_rerun()
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(f"Failed to confirm tutor: {e}")
                if st.button("Deny", key=f"deny_{tid}"):
                    try:
                        supabase.table('tutors').update({"approved": False}).eq('id', tid).execute()
                        st.info(f"Denied {name}")
                        try:
                            st.experimental_rerun()
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(f"Failed to deny tutor: {e}")

st.markdown("---")

# Keep existing editor for confirmed tutors below
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

                st.markdown("---")
                st.subheader("Languages")
                afrikaans = st.checkbox("Afrikaans", value=bool(tutor.get('afrikaans')))
                isizulu = st.checkbox("IsiZulu", value=bool(tutor.get('isizulu')))
                setswana = st.checkbox("Setswana", value=bool(tutor.get('setswana')))
                isixhosa = st.checkbox("IsiXhosa", value=bool(tutor.get('isixhosa')))
                french = st.checkbox("French", value=bool(tutor.get('french')))

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
                        "afrikaans": bool(afrikaans),
                        "isizulu": bool(isizulu),
                        "setswana": bool(setswana),
                        "isixhosa": bool(isixhosa),
                        "french": bool(french),
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
