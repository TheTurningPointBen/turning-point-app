import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Tutor Dashboard")

# -------------------------
# AUTH CHECK
# -------------------------
if "user" not in st.session_state:
    st.warning("Please login first.")
    try:
        st.switch_page("pages/tutor_login.py")
    except Exception:
        st.stop()

user = st.session_state.user

# -------------------------
# FETCH TUTOR PROFILE
# -------------------------
profile_res = supabase.table("tutors") \
    .select("*") \
    .eq("user_id", user.id) \
    .execute()

profile = profile_res.data[0] if profile_res.data else None

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)

if not profile:
    st.subheader("Complete Your Tutor Profile")

    name = st.text_input("Name")
    surname = st.text_input("Surname")
    phone = st.text_input("Phone Number")
    town = st.text_input("Town")
    city = st.text_input("City")
    transport = st.checkbox("I have my own transport")
    roles = st.selectbox("Role", ["Reader", "Scribe", "Both"])

    if st.button("Save Profile"):
        if not all([name, surname, phone, town, city]):
            st.error("All fields are required.")
        else:
            try:
                insert_res = supabase.table("tutors").insert({
                    "user_id": user.id,
                    "name": name,
                    "surname": surname,
                    "phone": phone,
                    "town": town,
                    "city": city,
                    "transport": transport,
                    "roles": roles
                
                }).execute()

                if getattr(insert_res, 'error', None) is None:
                    st.success("Profile submitted. Await admin approval.")
                    safe_rerun()
                else:
                    st.error(f"Failed to submit profile: {getattr(insert_res, 'error', None)}")
            except Exception as e:
                st.error(f"Submission error: {e}")

    st.stop()

from datetime import date

st.subheader("My Availability")

if not profile.get("approved"):
    st.info("Your profile is pending admin approval. Availability will be enabled once approved.")
else:
    avail_date = st.date_input("Available Date", min_value=date.today())
    start_time = st.time_input("Available From")
    end_time = st.time_input("Available Until")

    if st.button("Add Availability"):
        if start_time >= end_time:
            st.error("Invalid time range.")
        else:
            try:
                supabase.table("tutor_availability").insert({
                    "tutor_id": profile["id"],
                    "available_date": avail_date.isoformat(),
                    "start_time": start_time.strftime("%H:%M:%S"),
                    "end_time": end_time.strftime("%H:%M:%S")
                }).execute()

                st.success("Availability added.")
                safe_rerun()
            except Exception as e:
                st.error(f"Failed to add availability: {e}")

    # Show existing availability for this tutor
    try:
        avail_res = supabase.table("tutor_availability") \
            .select("*") \
            .eq("tutor_id", profile["id"]) \
            .order("available_date") \
            .execute()

        if avail_res.data:
            st.subheader("My Scheduled Availability")
            for a in avail_res.data:
                st.write(f"{a['available_date']} | {a['start_time']} – {a['end_time']}")
        else:
            st.info("No availability scheduled yet.")
    except Exception as e:
        st.error(f"Could not load availability: {e}")

# (Language fields removed from UI for now)
