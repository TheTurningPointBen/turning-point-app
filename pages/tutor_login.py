import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Tutor Login")
except Exception:
    pass
# Hide Streamlit Pages list in the sidebar for a cleaner login
st.markdown(
    """
    <script>
    (function(){
        const hide = ()=>{
            try{
                const divs = Array.from(document.querySelectorAll('div'));
                for(const d of divs){
                    if(d.innerText && (d.innerText.trim().startsWith('Pages') || d.innerText.trim().startsWith('Page'))){
                        let node = d;
                        while(node && node.tagName !== 'ASIDE') node = node.parentElement;
                        if(node) node.remove(); else d.remove();
                        break;
                    }
                }
            }catch(e){}
        };
        setTimeout(hide, 200);
    })();
    </script>
    """,
    unsafe_allow_html=True,
)
from utils.session import get_supabase, restore_session_from_refresh
import json
try:
    from config import SUPABASE_URL
except Exception:
    SUPABASE_URL = None

supabase = get_supabase()

# Auto-restore session from refresh token if one was passed once in the URL
params = {}
try:
    params = st.query_params or {}
except Exception:
    params = {}

if params.get('tp_rt'):
    token = params.get('tp_rt')[0]
    restored = restore_session_from_refresh(token)
    if restored and restored.get('user'):
        st.session_state['authenticated'] = True
        st.session_state['user'] = restored.get('user')
        st.session_state['email'] = restored.get('user', {}).get('email')
        try:
            st.experimental_set_query_params()
        except Exception:
            pass
        try:
            st.experimental_rerun()
        except Exception:
            pass

# Handle password recovery links sent by Supabase (e.g. ?type=recovery&access_token=...)
try:
    qp_type = (params.get('type') or [None])[0]
    qp_token = (params.get('access_token') or [None])[0]
except Exception:
    qp_type = None
    qp_token = None

if qp_type == 'recovery' and qp_token:
    # Redirect recovery links to the dedicated password_reset page
    try:
        # Build redirect URL preserving the token
        redirect_url = f"/password_reset?type=recovery&access_token={qp_token}"
        st.markdown(f"<script>window.location.href='{redirect_url}';</script>", unsafe_allow_html=True)
    except Exception:
        st.error('Unable to redirect to password reset page. Please open the password reset link from your email.')
    st.stop()

st.title("Tutor Portal")

tab1, tab2 = st.tabs(["Login", "Register"])

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)

# -------------------------
# LOGIN
# -------------------------
with tab1:
    st.subheader("Tutor Login")

    # If a refresh token exists in localStorage, send it once via URL so
    # the server can restore the session (we remove it from URL afterwards).
    st.markdown(
        """
        <script>
        (function(){
            try{
                const rt = localStorage.getItem('tp_refresh');
                if(rt && !window.location.search.includes('tp_rt=')){
                    const url = new URL(window.location.href);
                    url.searchParams.set('tp_rt', rt);
                    // Don't keep the token in localStorage if we just pushed it
                    // (we'll remove it later on successful restore)
                    window.location.replace(url.toString());
                }
                // Otherwise, prefill email if stored
                const v = localStorage.getItem('tp_email_tutor');
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

    email = st.text_input("Email", key="login_email")
    remember = st.checkbox("Remember me", key="remember_tutor")
    password = st.text_input("Password", type="password", key="login_pw")

    if st.button("Login"):
        try:
            # Save email to localStorage if user opted in
            if remember:
                st.markdown(f"<script>localStorage.setItem('tp_email_tutor', {json.dumps(email)});</script>", unsafe_allow_html=True)
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            # If the response includes a refresh token and the user opted in,
            # persist it to localStorage so we can auto-restore later.
            try:
                session = getattr(res, 'session', None) or (res.get('session') if isinstance(res, dict) else None)
                refresh = None
                if session:
                    refresh = getattr(session, 'refresh_token', None) or (session.get('refresh_token') if isinstance(session, dict) else None)
                if not refresh:
                    refresh = getattr(res, 'refresh_token', None) or (res.get('refresh_token') if isinstance(res, dict) else None)
                if remember and refresh:
                    st.markdown(f"<script>localStorage.setItem('tp_refresh', {json.dumps(refresh)});</script>", unsafe_allow_html=True)
            except Exception:
                pass

            if getattr(res, 'user', None):
                st.session_state["authenticated"] = True
                st.session_state["user"] = res.user
                st.session_state["role"] = "tutor"
                st.session_state["email"] = getattr(res.user, 'email', None)
                st.success("Logged in successfully.")
                # Ensure tutors table has this user's email and user_id linked
                try:
                    user_obj = res.user
                    user_id = getattr(user_obj, 'id', None)
                    user_email = getattr(user_obj, 'email', None)
                except Exception:
                    user_id = None
                    user_email = getattr(res.user, 'email', None)

                try:
                    if user_id or user_email:
                        if user_id:
                            t_res = supabase.table('tutors').select('*').eq('user_id', user_id).execute()
                            if getattr(t_res, 'data', None) and len(t_res.data) > 0:
                                existing = t_res.data[0]
                                if user_email and existing.get('email') != user_email:
                                    supabase.table('tutors').update({'email': user_email}).eq('id', existing.get('id')).execute()
                            else:
                                if user_email:
                                    by_email = supabase.table('tutors').select('*').eq('email', user_email).execute()
                                    if getattr(by_email, 'data', None) and len(by_email.data) > 0:
                                        supabase.table('tutors').update({'user_id': user_id}).eq('id', by_email.data[0].get('id')).execute()
                                    else:
                                        supabase.table('tutors').insert({'user_id': user_id, 'email': user_email}).execute()
                        else:
                            if user_email:
                                by_email = supabase.table('tutors').select('*').eq('email', user_email).execute()
                                if not (getattr(by_email, 'data', None) and len(by_email.data) > 0):
                                    supabase.table('tutors').insert({'email': user_email}).execute()
                except Exception:
                    pass
                try:
                    st.switch_page("pages/tutor.py")
                except Exception:
                    safe_rerun()

        except Exception as e:
            st.error("Invalid login credentials.")
            try:
                st.exception(e)
            except Exception:
                pass

    # -------------------------
    # FORGOT PASSWORD
    # -------------------------
    with st.expander("Forgot password?"):
        fp_email = st.text_input("Enter your account email to receive reset instructions", key="tutor_forgot_email")
        if st.button("Send reset email", key="tutor_forgot_send"):
            if not fp_email:
                st.error("Please enter your email.")
            else:
                try:
                    from utils.session import generate_recovery_link
                    from utils.email import send_email
                    import os

                    site = os.getenv('SITE_URL') or os.getenv('APP_URL') or 'http://localhost:8501'
                    gen = generate_recovery_link(fp_email, redirect_to=site + '/password_reset')
                    if gen.get('ok'):
                        raw_link = gen.get('direct_link') or gen.get('link')
                        try:
                            from urllib.parse import urlparse, parse_qs
                            p = urlparse(raw_link)
                            token = None
                            q = parse_qs(p.query)
                            if 'access_token' in q:
                                token = q.get('access_token')[0]
                            if not token and p.fragment:
                                fq = parse_qs(p.fragment)
                                if 'access_token' in fq:
                                    token = fq.get('access_token')[0]
                        except Exception:
                            token = None

                        if token:
                            link = site.rstrip('/') + f"/password_reset?type=recovery&access_token={token}"
                        else:
                            link = raw_link

                        subj = 'Turning Point — Password reset instructions'
                        plain = f"Follow this link to reset your password: {link}\nIf you did not request this, ignore this email."
                        html = f"<p>Follow this link to reset your password:</p><p><a href=\"{link}\">Reset password</a></p>"
                        send_res = send_email(fp_email, subj, body=plain, html=html)
                        if send_res.get('ok'):
                            st.success('If that email exists, password reset instructions have been sent.')
                        else:
                            st.warning('Password reset request could not be sent — please contact support.')
                    else:
                        st.warning('Password reset request could not be sent — please contact support.')
                except Exception as e:
                    st.error('Failed to request password reset. Please try again later.')
                    try:
                        st.exception(e)
                    except Exception:
                        pass

# -------------------------
# REGISTER
# -------------------------
with tab2:
    st.subheader("Tutor Registration")

    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Password", type="password", key="reg_pw")
    confirm_pw = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if reg_password != confirm_pw:
            st.error("Passwords do not match.")
        else:
            try:
                res = supabase.auth.sign_up({
                    "email": reg_email,
                    "password": reg_password
                })

                if getattr(res, 'user', None):
                    st.success("Thank you please log in to account.")
                    # Create a minimal tutors record for this new user
                    try:
                        user_obj = res.user
                        user_id = getattr(user_obj, 'id', None)
                        user_email = getattr(user_obj, 'email', None)
                    except Exception:
                        user_id = None
                        user_email = reg_email

                    try:
                        # If a tutors record already exists for this email, link the user_id
                        if user_email:
                            existing = supabase.table('tutors').select('*').eq('email', user_email).execute()
                            if getattr(existing, 'data', None) and len(existing.data) > 0:
                                # update the existing tutor row with user_id (if available) and ensure email stored
                                upd_payload = {}
                                if user_id:
                                    upd_payload['user_id'] = user_id
                                upd_payload['email'] = user_email
                                supabase.table('tutors').update(upd_payload).eq('id', existing.data[0].get('id')).execute()
                            else:
                                # create a new tutor row
                                payload = {'email': user_email}
                                if user_id:
                                    payload['user_id'] = user_id
                                supabase.table('tutors').insert(payload).execute()
                        else:
                            # Fallback: create a minimal row if we don't have an email
                            if user_id:
                                supabase.table('tutors').insert({'user_id': user_id}).execute()
                    except Exception:
                        pass

            except Exception as e:
                st.error("Registration failed. Email may already exist.")
                try:
                    st.exception(e)
                except Exception:
                    pass
