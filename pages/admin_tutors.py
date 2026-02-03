import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Admin Tutors")
except Exception:
    pass
from utils.session import get_supabase
from utils.session import delete_auth_user, set_auth_user_password, get_supabase_service
import os
from utils.email import send_email
import secrets
import string

supabase = get_supabase()

st.title("Admin – Tutor Approval")

# Top-left small Back button that returns to the Admin Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_dashboard_tutors"):
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

res = supabase.table("tutors") \
    .select("*") \
    .order("created_at", desc=True) \
    .execute()

if not res.data:
    st.info("No tutors found.")
    st.stop()

for tutor in res.data:
    with st.expander(f"{tutor.get('name')} {tutor.get('surname')}"):
        st.write(f"📞 {tutor.get('phone')}")
        st.write(f"📍 {tutor.get('town')}, {tutor.get('city')}")
        st.write(f"🚗 Transport: {'Yes' if tutor.get('transport') else 'No'}")
        st.write(f"🎓 Role: {tutor.get('roles')}")
        st.write(f"Status: {'Approved' if tutor.get('approved') else 'Pending'}")

        if not tutor.get("approved"):
            if st.button("Approve", key=str(tutor.get("id"))):
                supabase.table("tutors") \
                    .update({"approved": True}) \
                    .eq("id", tutor.get("id")) \
                    .execute()

                st.success("Tutor approved.")
                safe_rerun()

        # One-click: remove transport flag for this tutor
        if tutor.get('transport'):
            if st.button("Remove transport", key=f"remove_transport_{tutor.get('id')}"):
                try:
                    supabase.table('tutors').update({'transport': False}).eq('id', tutor.get('id')).execute()
                    st.success('Transport flag cleared for tutor')
                    safe_rerun()
                except Exception as e:
                    st.error(f'Failed to clear transport: {e}')

        # Allow admins to delete tutor records (require typing DELETE)
        del_rec_flag = f'confirm_delete_tutor_record_{tutor.get("id")}'
        if st.button("Delete tutor record", key=f"delete_tutor_{tutor.get('id')}"):
            st.session_state[del_rec_flag] = True

        if st.session_state.get(del_rec_flag):
            confirm = st.text_input('Type DELETE to confirm deletion of this tutor record', key=f'del_rec_input_{tutor.get("id")}')
            col1, col2 = st.columns([1, 3])
            with col1:
                if confirm == 'DELETE' and st.button('Confirm delete record', key=f'confirm_delete_tutor_record_confirm_{tutor.get("id")}'):
                    try:
                        supabase.table('tutors').delete().eq('id', tutor.get('id')).execute()
                        # audit
                        try:
                            svc = get_supabase_service()
                            svc.table('admin_actions').insert({
                                'admin_email': st.session_state.get('email'),
                                'action': 'delete_tutor_record',
                                'target_type': 'tutor',
                                'target_id': str(tutor.get('id')),
                                'details': {}
                            }).execute()
                        except Exception:
                            pass
                        try:
                            from utils.email import send_admin_email
                            send_admin_email('Admin action: delete tutor record', f"Admin {st.session_state.get('email')} deleted tutor record {tutor.get('id')}")
                        except Exception:
                            pass
                        st.success('Tutor record deleted.')
                        safe_rerun()
                    except Exception as e:
                        st.error(f'Failed to delete tutor: {e}')
            with col2:
                if st.button('Cancel', key=f'confirm_delete_tutor_record_cancel_{tutor.get("id")}'):
                    st.session_state.pop(del_rec_flag, None)

        # If tutor has a linked auth user_id, allow deleting the Auth user (requires SUPABASE_SERVICE_ROLE env var)
        user_id = tutor.get('user_id')
        if user_id:
            delete_flag = f'confirm_delete_auth_{tutor.get("id")}'
            setpw_flag = f'confirm_set_pw_{tutor.get("id")}'

            # Delete linked auth user — require typing DELETE to confirm
            if st.button('Delete linked Auth user', key=f'delete_auth_{tutor.get("id")}'):
                st.session_state[delete_flag] = True

            if st.session_state.get(delete_flag):
                confirm = st.text_input('Type DELETE to confirm deletion', key=f'del_input_{tutor.get("id")}')
                colc, cola = st.columns([1, 3])
                with colc:
                    if confirm == 'DELETE' and st.button('Confirm delete', key=f'confirm_delete_auth_confirm_{tutor.get("id")}'):
                        res = delete_auth_user(user_id)
                        # record audit
                        try:
                            svc = get_supabase_service()
                            svc.table('admin_actions').insert({
                                'admin_email': st.session_state.get('email'),
                                'action': 'delete_auth_user',
                                'target_type': 'tutor',
                                'target_id': str(tutor.get('id')),
                                'details': {'user_id': user_id}
                            }).execute()
                        except Exception:
                            pass
                        st.session_state.pop(delete_flag, None)
                        if res.get('ok'):
                            st.success('Supabase Auth user deleted.')
                        else:
                            st.error(f"Failed to delete auth user: {res.get('error')}")
                        try:
                            from utils.email import send_admin_email
                            send_admin_email('Admin action: delete auth user', f"Admin {st.session_state.get('email')} deleted auth user {user_id} for tutor {tutor.get('id')}")
                        except Exception:
                            pass
                        safe_rerun()
                with cola:
                    if st.button('Cancel', key=f'confirm_delete_auth_cancel_{tutor.get("id")}'):
                        st.session_state.pop(delete_flag, None)

            # Set temporary password — keep confirm then record audit + notify
            svc_configured = bool(os.getenv('SUPABASE_SERVICE_ROLE'))
            if not svc_configured:
                st.warning('SUPABASE_SERVICE_ROLE not configured — admin password resets are disabled. Add the service role key to your environment to enable this feature.')
            else:
                if st.button('Set temporary password and email user', key=f"set_pw_{tutor.get('id')}"):
                    st.session_state[setpw_flag] = True

            if st.session_state.get(setpw_flag):
                st.info('A temporary password will be generated and emailed to the tutor.')
                colx, coly = st.columns([1, 3])
                with colx:
                    if st.button('Confirm set password', key=f'confirm_set_pw_confirm_{tutor.get("id")}'):
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
                                        from utils.email import send_admin_email
                                        send_admin_email('Admin action: set temporary password', f"Admin {st.session_state.get('email')} set temporary password for tutor {tutor.get('id')}")
                                    except Exception:
                                        pass
                                    st.success('Temporary password set and emailed to the tutor.')
                                    safe_rerun()
                                else:
                                    st.warning('Password set but failed to send email to tutor. See details.')
                                    st.write(mail.get('error'))
                            else:
                                st.error(f"Failed to set password: {resp.get('error')}")
                with coly:
                    if st.button('Cancel', key=f'confirm_set_pw_cancel_{tutor.get("id")}'):
                        st.session_state.pop(setpw_flag, None)
