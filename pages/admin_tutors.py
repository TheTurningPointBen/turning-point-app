import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Admin Tutors")
except Exception:
    pass
from utils.session import get_supabase

supabase = get_supabase()

st.title("Admin – Tutor Approval")

# Top-left small Back button that returns to the Admin Dashboard
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_dashboard_tutors"):
        st.switch_page("pages/admin_dashboard.py")

    st.markdown(
        """
        <style>
        .admin-back-space{height:4px}
        </style>
        <div class="admin-back-space"></div>
        <script>
        (function(){
            const label = '⬅️ Back';
            const apply = ()=>{
                const btns = Array.from(document.querySelectorAll('button'));
                for(const b of btns){
                    if(b.innerText && b.innerText.trim()===label){
                        b.style.background = '#0d6efd';
                        b.style.color = '#ffffff';
                        b.style.padding = '4px 8px';
                        b.style.borderRadius = '6px';
                        b.style.border = '0';
                        b.style.fontWeight = '600';
                        b.style.boxShadow = 'none';
                        b.style.cursor = 'pointer';
                        b.style.fontSize = '12px';
                        b.style.lineHeight = '16px';
                        b.style.display = 'inline-block';
                        b.style.margin = '0 8px 0 0';
                        b.style.verticalAlign = 'middle';
                        break;
                    }
                }
            };
            setTimeout(apply, 200);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

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

        # One-click: remove transport flag for this tutor
        if tutor.get('transport'):
            if st.button("Remove transport", key=f"remove_transport_{tutor.get('id')}"):
                try:
                    supabase.table('tutors').update({'transport': False}).eq('id', tutor.get('id')).execute()
                    st.success('Transport flag cleared for tutor')
                    safe_rerun()
                except Exception as e:
                    st.error(f'Failed to clear transport: {e}')

        # Allow admins to delete tutor records
        if st.button("Delete tutor record", key=f"delete_tutor_{tutor.get('id')}"):
            try:
                supabase.table('tutors').delete().eq('id', tutor.get('id')).execute()
                st.success('Tutor record deleted.')
                safe_rerun()
            except Exception as e:
                st.error(f'Failed to delete tutor: {e}')
