import streamlit as st
from utils.database import supabase

# Make sure user is logged in
if "user" in st.session_state:
    user = st.session_state["user"]

    # Check if profile exists
    profile_res = supabase.table("parents").select("*").eq("user_id", user.id).execute()
    profile = profile_res.data[0] if profile_res.data else None

    if profile:
        st.success(f"Welcome back, {profile['parent_name']}!")
        st.write(f"Child: {profile['child_name']}, Grade: {profile['grade']}, School: {profile['school']}")
        st.info("You can now proceed to booking (coming next).")
    else:
        st.warning("Please complete your profile to proceed.")

        parent_name = st.text_input("Parent Name")
        phone = st.text_input("Phone Number")
        child_name = st.text_input("Child Name")
        grade = st.text_input("Child Grade")
        school = st.text_input("Child School")

        if st.button("Save Profile"):
            if parent_name and phone and child_name and grade and school:
                insert_res = supabase.table("parents").insert({
                    "user_id": user.id,
                    "parent_name": parent_name,
                    "phone": phone,
                    "child_name": child_name,
                    "grade": grade,
                    "school": school
                }).execute()

                if getattr(insert_res, 'error', None) is None and insert_res.data:
                    st.success("Profile saved successfully! You can now book a reader/scribe.")
                    try:
                        st.experimental_rerun()
                    except Exception:
                        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                else:
                    st.error(f"Failed to save profile. Error: {getattr(insert_res, 'error', None)}")
            else:
                st.error("Please fill in all fields.")
else:
    st.info("Please log in first via the Parent Portal.")
