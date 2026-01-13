import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Admin – Tutor Approval")

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)

res = supabase.table("tutors") \
    .select("*") \
    .order("created_at", desc=True) \
    .execute()

if not res.data:
    st.info("No tutors found.")
    st.stop()

for tutor in res.data:
    with st.expander(f"{tutor.get('name')} {tutor.get('surname')}"):
        st.write(f"📞 {tutor.get('phone')}")
        st.write(f"📍 {tutor.get('town')}, {tutor.get('city')}")
        st.write(f"🚗 Transport: {'Yes' if tutor.get('transport') else 'No'}")
        st.write(f"🎓 Role: {tutor.get('roles')}")
        st.write(f"Status: {'Approved' if tutor.get('approved') else 'Pending'}")

        if not tutor.get("approved"):
            if st.button("Approve", key=str(tutor.get("id"))):
                supabase.table("tutors") \
                    .update({"approved": True}) \
                    .eq("id", tutor.get("id")) \
                    .execute()

                st.success("Tutor approved.")
                safe_rerun()
