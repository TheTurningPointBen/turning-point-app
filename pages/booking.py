import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()

st.set_page_config(page_title="Booking (removed)")

st.title("Booking")
st.warning("This legacy Booking page has been removed. Use 'Make a Booking' from the Parent Dashboard instead.")

if st.button("Go to Parent Booking"):
    try:
        try:
            st.query_params = {}
        except Exception:
            pass
        st.session_state.role = 'parent'
        st.switch_page("pages/parent_booking.py")
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass