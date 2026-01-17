import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY


def init_session():
    defaults = {
        "authenticated": False,
        "user": None,
        "role": None,
        "email": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource
def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    return create_client(SUPABASE_URL, SUPABASE_KEY)
