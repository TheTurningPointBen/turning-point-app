import streamlit as st
from utils.ui import hide_sidebar
from utils.database import supabase
from utils.session import restore_session_from_refresh

hide_sidebar()
try:
    st.set_page_config(page_title="Parent Login")
except Exception:
    pass

st.title("Parent Portal")

# Inject JS to auto-restore session from refresh token stored in localStorage
# and to prefill the email input if the user opted to remember it.
st.markdown(
    """
    <script>
    (function(){
        try{
            const rt = localStorage.getItem('tp_refresh');
            if(rt && !window.location.search.includes('tp_rt=')){
                const url = new URL(window.location.href);
                url.searchParams.set('tp_rt', rt);
                window.location.replace(url.toString());
            }
            // Prefill remembered parent email
            const v = localStorage.getItem('tp_email_parent');
            if(v){
                const labels = Array.from(document.querySelectorAll('label'));
                for(const l of labels){
                    if(l.innerText && l.innerText.trim()==='Email'){
                        const input = l.parentElement.querySelector('input') || l.nextElementSibling || l.parentElement.nextElementSibling.querySelector('input');
                        if(input){ input.value = v; input.dispatchEvent(new Event('input',{bubbles:true})); break; }
                    }
                }
            }
        }catch(e){}
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    st.subheader("Parent Login")

    # Attempt to restore session from a one-time token if present
    params = {}
    try:
        params = st.query_params or {}
    except Exception:
        params = {}

    if params.get('tp_rt'):
        token = params.get('tp_rt')[0]
        try:
            restored = restore_session_from_refresh(token)
            if restored and restored.get('user'):
                st.session_state['authenticated'] = True
                st.session_state['user'] = restored.get('user')
                st.session_state['role'] = 'parent'
                st.session_state['email'] = restored.get('user', {}).get('email')
                try:
                    st.experimental_set_query_params()
                except Exception:
                    pass
                try:
                    st.experimental_rerun()
                except Exception:
                    pass
        except Exception:
            pass

    email = st.text_input("Email", key="parent_login_email")
    password = st.text_input("Password", type="password", key="parent_login_pw")
    remember = st.checkbox("Remember me", key="remember_parent")

    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})

            # Persist refresh token to localStorage when requested (so we can
            # restore sessions across page reloads). We try to extract the
            # refresh token from the response in several possible shapes.
            try:
                session = getattr(res, 'session', None) or (res.get('session') if isinstance(res, dict) else None)
                refresh = None
                if session:
                    refresh = getattr(session, 'refresh_token', None) or (session.get('refresh_token') if isinstance(session, dict) else None)
                if not refresh:
                    refresh = getattr(res, 'refresh_token', None) or (res.get('refresh_token') if isinstance(res, dict) else None)
                if remember and refresh:
                    import json as _json
                    st.markdown(f"<script>localStorage.setItem('tp_refresh', {_json.dumps(refresh)});</script>", unsafe_allow_html=True)
                    # also remember the email separately for prefill
                    st.markdown(f"<script>localStorage.setItem('tp_email_parent', {_json.dumps(email)});</script>", unsafe_allow_html=True)
            except Exception:
                pass

            if not getattr(res, 'user', None):
                st.error("Login failed. Check credentials or confirm your email.")
                with st.expander("Server response (debug)"):
                    try:
                        if isinstance(res, dict):
                            st.json(res)
                        else:
                            st.write(res)
                    except Exception:
                        try:
                            st.write(res.__dict__)
                        except Exception:
                            st.write(str(res))
                try:
                    st.stop()
                except Exception:
                    pass

            # Successful login: set session and ensure parents table links to auth user
            user_obj = res.user
            user_id = getattr(user_obj, 'id', None)
            user_email = getattr(user_obj, 'email', None) or email

            st.session_state['authenticated'] = True
            st.session_state['user'] = user_obj
            st.session_state['role'] = 'parent'
            st.session_state['email'] = user_email
            st.success("Logged in successfully.")

            try:
                if user_id or user_email:
                    if user_id:
                        p_res = supabase.table('parents').select('*').eq('user_id', user_id).execute()
                        if getattr(p_res, 'data', None) and len(p_res.data) > 0:
                            existing = p_res.data[0]
                            if user_email and existing.get('email') != user_email:
                                supabase.table('parents').update({'email': user_email}).eq('id', existing.get('id')).execute()
                        else:
                            if user_email:
                                by_email = supabase.table('parents').select('*').eq('email', user_email).execute()
                                if getattr(by_email, 'data', None) and len(by_email.data) > 0:
                                    supabase.table('parents').update({'user_id': user_id}).eq('id', by_email.data[0].get('id')).execute()
                                else:
                                    supabase.table('parents').insert({'user_id': user_id, 'email': user_email}).execute()
                    else:
                        if user_email:
                            by_email = supabase.table('parents').select('*').eq('email', user_email).execute()
                            if not (getattr(by_email, 'data', None) and len(by_email.data) > 0):
                                supabase.table('parents').insert({'email': user_email}).execute()
            except Exception:
                pass

            try:
                st.switch_page("pages/parent_dashboard.py")
            except Exception:
                try:
                    st.experimental_rerun()
                except Exception:
                    pass
        except Exception as e:
            st.error("Login exception. Please try again later.")
            try:
                st.exception(e)
            except Exception:
                pass

    with st.expander("Forgot password?"):
        fp_email = st.text_input("Enter your account email to receive reset instructions", key="parent_forgot_email")
        if st.button("Send reset email", key="parent_forgot_send"):
            if not fp_email:
                st.error("Please enter your email.")
            else:
                try:
                    try:
                        res = supabase.auth.reset_password_for_email(fp_email)
                    except Exception:
                        try:
                            res = supabase.auth.api.reset_password_for_email(fp_email)
                        except Exception:
                            res = None

                    if res is None:
                        st.warning("Password reset request could not be sent — please contact support.")
                    else:
                        st.success("If that email exists, password reset instructions have been sent.")
                except Exception as e:
                    st.error("Failed to request password reset. Please try again later.")
                    try:
                        st.exception(e)
                    except Exception:
                        pass

# Registration block continues below

with tab2:
    st.subheader("Parent Registration")
    reg_email = st.text_input("Email", key="parent_reg_email")
    reg_password = st.text_input("Password", type="password", key="parent_reg_pw")
    confirm_pw = st.text_input("Confirm Password", type="password", key="parent_reg_confirm")

    if st.button("Register"):
        if reg_password != confirm_pw:
            st.error("Passwords do not match.")
        else:
            try:
                res = supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                # Regardless of whether Supabase returns a user object (depends
                # on email confirmation settings), store the registration email
                # in session so the user can be redirected to complete their
                # profile immediately.
                try:
                    user_obj = res.user if getattr(res, 'user', None) else None
                    user_email = getattr(user_obj, 'email', None) if user_obj else reg_email
                except Exception:
                    user_obj = None
                    user_email = reg_email

                st.session_state['authenticated'] = True
                st.session_state['user'] = user_obj or {'email': user_email}
                st.session_state['role'] = 'parent'
                st.session_state['email'] = user_email
                st.success("Registration successful — please complete your profile.")

                # Ensure a minimal parents record exists with this email/user_id
                try:
                    try:
                        user_obj = res.user
                        user_id = getattr(user_obj, 'id', None)
                        user_email = getattr(user_obj, 'email', None)
                    except Exception:
                        user_id = None
                        user_email = reg_email

                    try:
                        # If a parents record exists by user_id, update email if missing
                        if user_id:
                            p_res = supabase.table('parents').select('*').eq('user_id', user_id).execute()
                            if getattr(p_res, 'data', None) and len(p_res.data) > 0:
                                existing = p_res.data[0]
                                if user_email and existing.get('email') != user_email:
                                    supabase.table('parents').update({'email': user_email}).eq('id', existing.get('id')).execute()
                            else:
                                # Try to find by email and attach user_id
                                if user_email:
                                    by_email = supabase.table('parents').select('*').eq('email', user_email).execute()
                                    if getattr(by_email, 'data', None) and len(by_email.data) > 0:
                                        supabase.table('parents').update({'user_id': user_id}).eq('id', by_email.data[0].get('id')).execute()
                                    else:
                                        # Insert a minimal parent record
                                        supabase.table('parents').insert({'user_id': user_id, 'email': user_email}).execute()
                        else:
                            # No user_id available; ensure a parents row for the email exists
                            if user_email:
                                by_email = supabase.table('parents').select('*').eq('email', user_email).execute()
                                if not (getattr(by_email, 'data', None) and len(by_email.data) > 0):
                                    supabase.table('parents').insert({'email': user_email}).execute()
                    except Exception:
                        pass

                    # After ensuring a minimal parent record exists, send the
                    # user to the Parent Profile page so they can fill in details.
                    try:
                        st.switch_page("pages/parent_profile.py")
                    except Exception:
                        try:
                            st.experimental_rerun()
                        except Exception:
                            pass
                except Exception:
                    pass
                else:
                    st.error("Registration may have failed; see response below.")
                    st.write(res)
            except Exception as e:
                st.error("Registration failed. Email may already exist.")
                st.exception(e)

st.markdown("---")
st.caption("If you receive a verification email that fails to open, ensure your Supabase project 'Site URL' and 'Redirect URLs' include the Streamlit URL (http://localhost:8501).")

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
