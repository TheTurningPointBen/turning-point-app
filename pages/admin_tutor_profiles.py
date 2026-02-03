import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from utils.database import supabase
from utils.email import send_email, send_admin_email
from utils.session import set_auth_user_password, get_supabase_service
import os
import secrets
import string

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
                if st.button("Edit", key=f"edit_unconfirmed_{tid}"):
                    st.session_state[f"editing_unconfirmed_{tid}"] = True

            # Inline edit for unconfirmed tutor
            if st.session_state.get(f"editing_unconfirmed_{tid}"):
                try:
                    t_res = supabase.table('tutors').select('*').eq('id', tid).execute()
                    tutor = (t_res.data or [None])[0]
                except Exception as e:
                    st.error(f"Failed to load tutor for edit: {e}")
                    tutor = None

                if tutor:
                    with st.form(key=f"edit_unconfirmed_form_{tid}"):
                        name_in = st.text_input("First name", value=tutor.get('name') or "")
                        surname_in = st.text_input("Surname", value=tutor.get('surname') or "")
                        phone_in = st.text_input("Phone", value=tutor.get('phone') or "")
                        email_in = st.text_input("Email", value=tutor.get('email') or "")
                        city_in = st.text_input("City", value=tutor.get('city') or "")
                        roles_in = st.text_input("Roles (Reader/Scribe/Both/Invigilator/Prompter/All of the Above)", value=tutor.get('roles') or "")
                        notes_in = st.text_area("Notes", value=tutor.get('notes') or "")
                        approved_in = st.checkbox("Approved", value=bool(tutor.get('approved')))

                        st.markdown("---")
                        st.subheader("Languages")
                        afrikaans_in = st.checkbox("Afrikaans", value=bool(tutor.get('afrikaans')))
                        isizulu_in = st.checkbox("IsiZulu", value=bool(tutor.get('isizulu')))
                        setswana_in = st.checkbox("Setswana", value=bool(tutor.get('setswana')))
                        isixhosa_in = st.checkbox("IsiXhosa", value=bool(tutor.get('isixhosa')))
                        french_in = st.checkbox("French", value=bool(tutor.get('french')))

                        save = st.form_submit_button("Save changes")
                        cancel = st.form_submit_button("Cancel")

                        if cancel:
                            st.session_state.pop(f"editing_unconfirmed_{tid}", None)
                            try:
                                st.experimental_rerun()
                            except Exception:
                                pass

                        if save:
                            payload = {}
                            existing_keys = set(tutor.keys())
                            fields = {
                                'name': name_in,
                                'surname': surname_in,
                                'phone': phone_in,
                                'email': email_in,
                                'city': city_in,
                                'roles': roles_in,
                                'notes': notes_in,
                                'approved': approved_in,
                                'afrikaans': bool(afrikaans_in),
                                'isizulu': bool(isizulu_in),
                                'setswana': bool(setswana_in),
                                'isixhosa': bool(isixhosa_in),
                                'french': bool(french_in),
                            }
                            for k, v in fields.items():
                                if k in existing_keys:
                                    payload[k] = v

                            if not payload:
                                st.info("No updatable columns found for this tutor.")
                            else:
                                try:
                                    upd = supabase.table('tutors').update(payload).eq('id', tid).execute()
                                    if getattr(upd, 'error', None) is None:
                                        st.success("Tutor profile updated")
                                        st.session_state.pop(f"editing_unconfirmed_{tid}", None)
                                        try:
                                            st.experimental_rerun()
                                        except Exception:
                                            pass
                                    else:
                                        st.error(f"Update failed: {getattr(upd, 'error', upd)}")
                                except Exception as e:
                                    st.error(f"Failed to update tutor: {e}")

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
                roles = st.text_input("Roles (Reader/Scribe/Both/Invigilator/Prompter/All of the Above)", value=tutor.get('roles') or "")
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

            # Allow admin to set a temporary password for the tutor if they have a linked auth user
            user_id = tutor.get('user_id')
            if user_id:
                setpw_flag = f'confirm_set_pw_{tutor_id}'

                svc_configured = bool(os.getenv('SUPABASE_SERVICE_ROLE'))
                if not svc_configured:
                    st.warning('SUPABASE_SERVICE_ROLE not configured — admin password resets are disabled. Add the service role key to your environment to enable this feature.')
                else:
                    if st.button('Set temporary password and email tutor', key=f"set_pw_{tutor_id}"):
                        st.session_state[setpw_flag] = True

                if st.session_state.get(setpw_flag):
                    st.info('A temporary password will be generated and emailed to the tutor.')
                    colx, coly = st.columns([1, 3])
                    with colx:
                        if st.button('Confirm set password', key=f'confirm_set_pw_confirm_{tutor_id}'):
                            tutor_email = tutor.get('email')
                            st.session_state.pop(setpw_flag, None)
                            if not tutor_email:
                                st.error('Tutor has no email on file; cannot email temporary password.')
                            else:
                                alphabet = string.ascii_letters + string.digits
                                temp_pw = ''.join(secrets.choice(alphabet) for _ in range(12))
                                resp = set_auth_user_password(user_id, temp_pw)
                                if resp.get('ok'):
                                    subject = 'Your temporary password'
                                    body = f"Hello {tutor.get('name') or ''},\n\nAn administrator has set a temporary password for your account.\n\nTemporary password: {temp_pw}\n\nPlease log in and change your password immediately.\n\nIf you did not request this, contact the admin.\n"
                                    mail = send_email(tutor_email, subject, body)
                                    if mail.get('ok'):
                                        # audit and notify
                                        try:
                                            svc = get_supabase_service()
                                            svc.table('admin_actions').insert({
                                                'admin_email': st.session_state.get('email'),
                                                'action': 'set_temporary_password',
                                                'target_type': 'tutor',
                                                'target_id': str(tutor.get('id')),
                                                'details': {'user_id': user_id}
                                            }).execute()
                                        except Exception:
                                            pass
                                        try:
                                            send_admin_email('Admin action: set temporary password', f"Admin {st.session_state.get('email')} set temporary password for tutor {tutor.get('id')}")
                                        except Exception:
                                            pass
                                        st.success('Temporary password set and emailed to the tutor.')
                                        try:
                                            st.experimental_rerun()
                                        except Exception:
                                            pass
                                    else:
                                        st.warning('Password set but failed to send email to tutor. See details.')
                                        st.write(mail.get('error'))
                                else:
                                    st.error(f"Failed to set password: {resp.get('error')}")
                    with coly:
                        if st.button('Cancel', key=f'confirm_set_pw_cancel_{tutor_id}'):
                            st.session_state.pop(setpw_flag, None)
