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
from utils.session import get_supabase
import json

supabase = get_supabase()

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

    # Prefill email from localStorage if present (client-side)
    st.markdown(
        """
        <script>
        (function(){
            try{
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

            if getattr(res, 'user', None):
                st.session_state["authenticated"] = True
                st.session_state["user"] = res.user
                st.session_state["role"] = "tutor"
                st.session_state["email"] = getattr(res.user, 'email', None)
                st.success("Logged in successfully.")
                try:
                    st.switch_page("pages/tutor.py")
                except Exception:
                    safe_rerun()

        except Exception:
            st.error("Invalid login credentials.")

    # -------------------------
    # FORGOT PASSWORD
    # -------------------------
    with st.expander("Forgot password?"):
        fp_email = st.text_input("Enter your account email to receive reset instructions", key="forgot_email")
        if st.button("Send reset email", key="forgot_send"):
            if not fp_email:
                st.error("Please enter your email.")
            else:
                try:
                    # Try common supabase client methods for password reset
                    try:
                        res = supabase.auth.reset_password_for_email(fp_email)
                    except Exception:
                        try:
                            res = supabase.auth.api.reset_password_for_email(fp_email)
                        except Exception:
                            res = None

                    if res is None:
                        st.warning("Password reset request could not be sent — please check server logs or contact admin.")
                    else:
                        st.success("If that email exists in our system, password reset instructions have been sent.")
                except Exception as e:
                    st.error("Failed to request password reset. Please try again later.")
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
                    st.success(
                        "Registration successful. Please confirm your email before logging in."
                    )

            except Exception:
                st.error("Registration failed. Email may already exist.")
