import streamlit as st
st.set_page_config(page_title="Tutor Login")
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
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pw")

    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if getattr(res, 'user', None):
                st.session_state["user"] = res.user
                st.session_state["role"] = "tutor"
                st.success("Logged in successfully.")
                try:
                    st.switch_page("pages/tutor.py")
                except Exception:
                    safe_rerun()

        except Exception:
            st.error("Invalid login credentials.")

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
