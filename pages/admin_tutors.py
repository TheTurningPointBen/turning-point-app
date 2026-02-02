import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Admin Tutors")
except Exception:
    pass
from utils.session import get_supabase
from utils.session import delete_auth_user, set_auth_user_password
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

        # Allow admins to delete tutor records
        if st.button("Delete tutor record", key=f"delete_tutor_{tutor.get('id')}"):
            try:
                supabase.table('tutors').delete().eq('id', tutor.get('id')).execute()
                st.success('Tutor record deleted.')
                safe_rerun()
            except Exception as e:
                st.error(f'Failed to delete tutor: {e}')

        # If tutor has a linked auth user_id, allow deleting the Auth user (requires SUPABASE_SERVICE_ROLE env var)
        user_id = tutor.get('user_id')
        if user_id:
            if st.button('Delete linked Auth user', key=f'delete_auth_{tutor.get("id")}'):
                res = delete_auth_user(user_id)
                if res.get('ok'):
                    st.success('Supabase Auth user deleted.')
                    safe_rerun()
                else:
                    st.error(f"Failed to delete auth user: {res.get('error')}")

            # Allow admins to set a temporary password (will be emailed to the tutor)
            if st.button('Set temporary password and email user', key=f'set_pw_{tutor.get("id")}'):
                tutor_email = tutor.get('email')
                if not tutor_email:
                    st.error('Tutor has no email on file; cannot email temporary password.')
                else:
                    # generate a random 12-character temporary password
                    alphabet = string.ascii_letters + string.digits
                    temp_pw = ''.join(secrets.choice(alphabet) for _ in range(12))
                    resp = set_auth_user_password(user_id, temp_pw)
                    if resp.get('ok'):
                        # send email with the temporary password
                        subject = 'Your temporary password'
                        body = f"Hello {tutor.get('name') or ''},\n\nAn administrator has set a temporary password for your account.\n\nTemporary password: {temp_pw}\n\nPlease log in and change your password immediately.\n\nIf you did not request this, contact the admin.\n"
                        mail = send_email(tutor_email, subject, body)
                        if mail.get('ok'):
                            st.success('Temporary password set and emailed to the tutor.')
                            safe_rerun()
                        else:
                            st.warning('Password set but failed to send email to tutor. See details.')
                            st.write(mail.get('error'))
                    else:
                        st.error(f"Failed to set password: {resp.get('error')}")
