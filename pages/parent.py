import streamlit as st
st.set_page_config(page_title="Parent")
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
    email = st.text_input("Email", key="parent_login_email")
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
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    
                    if getattr(res, 'user', None):
                        st.session_state["user"] = res.user
                        st.session_state["role"] = "parent"
                        st.success("Logged in successfully.")
                        try:
                            st.switch_page("pages/parent_profile.py")
                        except Exception:
                            try:
                                st.experimental_rerun()
                            except Exception:
                                st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                    else:
                        st.error("Login failed. Check credentials or confirm your email.")
                        st.write(res)
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        st.warning(f"Connection issue. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        st.error("⚠️ Unable to connect to authentication service. Please check your internet connection and try again.")
                        with st.expander("Technical Details"):
                            st.exception(e)

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
