import streamlit as st
from utils.ui import hide_sidebar

# Apply shared hide-sidebar helper
hide_sidebar()
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
from utils.database import supabase
import time

st.title("Parent Portal")

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    st.subheader("Parent Login")
    # Prefill email from localStorage if present (client-side)
    st.markdown(
        """
        <script>
        (function(){
            try{
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

    email = st.text_input("Email", key="parent_login_email")
    remember = st.checkbox("Remember me", key="remember_parent")
    password = st.text_input("Password", type="password", key="parent_login_pw")

    if st.button("Login"):
        if not email or not password:
            st.error("Please provide both email and password.")
        else:
            # Retry logic for network issues
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    with st.spinner(f"Logging in... {f'(Attempt {attempt + 1}/{max_retries})' if attempt > 0 else ''}"):
                        # Save email to localStorage if user opted in
                        if remember:
                            import json
                            st.markdown(f"<script>localStorage.setItem('tp_email_parent', {json.dumps(email)});</script>", unsafe_allow_html=True)
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})

                    if getattr(res, 'user', None):
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = res.user
                        st.session_state["role"] = "parent"
                        st.session_state["email"] = getattr(res.user, 'email', None)
                        st.success("Logged in successfully.")
                        try:
                            st.switch_page("pages/parent_dashboard.py")
                        except Exception:
                            try:
                                st.experimental_rerun()
                            except Exception:
                                st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                    else:
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
                    break  # Success, exit retry loop

                except Exception as e:
                    # If Supabase returns an authentication error (bad credentials),
                    # surface it as a login failure rather than a transient connection issue.
                    try:
                        from supabase_auth.errors import AuthApiError
                        is_auth_error = isinstance(e, AuthApiError)
                    except Exception:
                        is_auth_error = False

                    if is_auth_error:
                        st.error("Login failed. Check credentials or confirm your email.")
                        with st.expander("Server response (debug)"):
                            st.exception(e)
                        break

                    # For other errors (network/timeouts), retry a few times.
                    if attempt < max_retries - 1:
                        st.warning(f"Connection issue. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        st.error("⚠️ Unable to connect to authentication service. Please check your internet connection and try again.")
                        with st.expander("Technical Details"):
                            st.exception(e)

    # -------------------------
    # FORGOT PASSWORD
    # -------------------------
    with st.expander("Forgot password?"):
        fp_email = st.text_input("Enter your account email to receive reset instructions", key="parent_forgot_email")
        if st.button("Send reset email", key="parent_forgot_send"):
            if not fp_email:
                st.error("Please enter your email.")
            else:
                try:
                    # Try the supabase client reset APIs; be defensive about client versions
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
                if getattr(res, 'user', None):
                    st.success("Registration successful. Please confirm your email before logging in.")
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
