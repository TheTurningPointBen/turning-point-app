import streamlit as st
from utils.ui import hide_sidebar

hide_sidebar()
from utils.database import supabase

# Ensure user is logged in
user = st.session_state.get("user")
if not user:
    st.info("Please log in first via the Parent Portal.")
    try:
        st.stop()
    except Exception:
        pass

# Helper to read attribute or dict key
def get_user_attr(u, key):
    try:
        return getattr(u, key)
    except Exception:
        try:
            return u.get(key) if isinstance(u, dict) else None
        except Exception:
            return None

user_id = get_user_attr(user, "id")

# Fetch parent profile by user_id
profile = None
try:
    if user_id is not None:
        res = supabase.table("parents").select("*").eq("user_id", user_id).execute()
        profile = res.data[0] if getattr(res, 'data', None) else None
except Exception:
    profile = None

if profile:
    # Small Back button to return to dashboard
    back_col, main_col = st.columns([1, 9])
    with back_col:
        if st.button("⬅️ Back", key="back_to_dashboard_profile"):
            try:
                st.switch_page("pages/parent_dashboard.py")
            except Exception:
                try:
                    st.experimental_rerun()
                except Exception:
                    pass

        st.markdown(
            """
            <style>
            .parent-back-space{height:4px}
            </style>
            <div class="parent-back-space"></div>
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

    st.success(f"Welcome back, {profile.get('parent_name', 'Parent')}!")

    # Show Parent Details
    st.subheader("Parent Details")
    p_col1, p_col2 = st.columns([2, 3])
    p_col1.markdown(f"**Name**\n\n{profile.get('parent_name', '—')}")
    p_col2.markdown(f"**Phone / Email**\n\n{profile.get('phone','—')} / {profile.get('email','—')}")

    st.markdown("---")

    # Show Child Details
    st.subheader("Child Details")
    c_name, c_grade, c_school = st.columns([2, 1, 2])
    c_name.markdown(f"**Name**\n\n{profile.get('child_name', '—')}")
    c_grade.markdown(f"**Grade**\n\n{profile.get('grade', '—')}")
    c_school.markdown(f"**School**\n\n{profile.get('school', '—')}")

    st.markdown("---")

    # Actions: Make a Booking / Your Bookings
    a1, a2, a3 = st.columns([1, 2, 1])
    with a2:
        if st.button("➕ Make a Booking", key="parent_proceed_booking"):
            try:
                st.switch_page("pages/parent_booking.py")
            except Exception:
                st.experimental_rerun()
        if st.button("📚 Your Bookings", key="parent_view_bookings"):
            try:
                st.switch_page("pages/parent_bookings.py")
            except Exception:
                st.experimental_rerun()

else:
    st.warning("Please complete your profile to proceed.")

    # Try to locate an existing parent profile by email
    user_email = get_user_attr(user, 'email')
    if user_email:
        try:
            alt = supabase.table('parents').select('*').eq('email', user_email).execute()
            if getattr(alt, 'data', None):
                with st.expander('Found parent record by email'):
                    st.write(alt.data[0])
        except Exception:
            pass

    st.info("Please complete your profile below:")
    parent_name = st.text_input("Parent Name")
    phone = st.text_input("Phone Number")
    child_name = st.text_input("Child Name")
    grade = st.text_input("Child Grade")
    school = st.text_input("Child School")

    if st.button("Save Profile"):
        if parent_name and phone and child_name and grade and school:
            payload = {
                "user_id": user_id,
                "parent_name": parent_name,
                "phone": phone,
                "child_name": child_name,
                "grade": grade,
                "school": school,
                "email": user_email,
            }
            try:
                insert_res = supabase.table("parents").insert(payload).execute()
            except Exception as e:
                st.error(f"Failed to save profile: {e}")
            else:
                if getattr(insert_res, 'error', None) is None and getattr(insert_res, 'data', None):
                    st.success("Profile saved successfully! You can now book a reader/scribe.")
                    try:
                        st.experimental_rerun()
                    except Exception:
                        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                else:
                    st.error(f"Failed to save profile. Error: {getattr(insert_res, 'error', None)}")
        else:
            st.error("Please fill in all fields.")

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
