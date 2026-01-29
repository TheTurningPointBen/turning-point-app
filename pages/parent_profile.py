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

    st.success(f"Welcome back, {profile.get('parent_name', 'Parent') }!")

    # Edit toggle
    if 'editing_profile' not in st.session_state:
        st.session_state['editing_profile'] = False

    if st.button("✏️ Edit Profile"):
        st.session_state['editing_profile'] = True

    # Display or edit profile
    if not st.session_state.get('editing_profile'):
        # Show Parent Details
        st.subheader("Parent Details")
        p_col1, p_col2 = st.columns([2, 3])
        p_col1.markdown(f"**Name**\n\n{profile.get('parent_name', '—')}")
        p_col2.markdown(f"**Phone / Email**\n\n{profile.get('phone','—')} / {profile.get('email','—')}")

        st.markdown("---")

        # Show Children
        st.subheader("Children")
        children = profile.get('children') or []
        # Fallback to older single-child fields
        if not children:
            first = profile.get('child_name') or profile.get('child_firstname') or None
            if first:
                children = [{'name': first, 'grade': profile.get('grade'), 'school': profile.get('school')}]

        if children:
            for i, c in enumerate(children):
                st.markdown(f"**Child {i+1}** — {c.get('name','—')} | Grade: {c.get('grade','—')} | School: {c.get('school','—')}")
        else:
            st.info("No child information available. Click Edit Profile to add child details.")

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
        # Editing form
        st.subheader("Edit Profile")
        parent_name = st.text_input("Parent Name", value=profile.get('parent_name') or '')
        phone = st.text_input("Phone Number", value=profile.get('phone') or '')
        # Allow editing the contact email stored on the parent profile
        email_value = profile.get('email') or get_user_attr(user, 'email') or ''
        email = st.text_input("Contact Email", value=email_value)
        # children editor
        existing_children = profile.get('children') or []
        if not existing_children:
            first = profile.get('child_name') or profile.get('child_firstname') or None
            if first:
                existing_children = [{'name': first, 'grade': profile.get('grade'), 'school': profile.get('school')}]

        if 'children_count' not in st.session_state:
            st.session_state['children_count'] = max(1, len(existing_children) or 1)

        # initialize input defaults
        for idx in range(st.session_state['children_count']):
            default = existing_children[idx] if idx < len(existing_children) else {'name':'','grade':'','school':''}
            st.text_input(f"Child {idx+1} Name", key=f"child_name_{idx}", value=default.get('name',''))
            st.text_input(f"Child {idx+1} Grade", key=f"child_grade_{idx}", value=default.get('grade',''))
            st.text_input(f"Child {idx+1} School", key=f"child_school_{idx}", value=default.get('school',''))

        col_add, col_save, col_cancel = st.columns([1,1,1])
        with col_add:
            if st.button("Add another child"):
                st.session_state['children_count'] += 1
                st.experimental_rerun()
        with col_cancel:
            if st.button("Cancel"):
                st.session_state['editing_profile'] = False
                st.experimental_rerun()
        with col_save:
            if st.button("Save Profile"):
                # gather children
                children = []
                for idx in range(st.session_state['children_count']):
                    name = st.session_state.get(f"child_name_{idx}", '').strip()
                    grade = st.session_state.get(f"child_grade_{idx}", '').strip()
                    school = st.session_state.get(f"child_school_{idx}", '').strip()
                    if name:
                        children.append({'name': name, 'grade': grade or None, 'school': school or None})

                payload = {
                    'parent_name': parent_name or None,
                    'phone': phone or None,
                    'email': (email or None),
                    'children': children or None,
                }
                # For backward compatibility, set first-child fields
                if children and len(children) > 0:
                    payload['child_name'] = children[0].get('name')
                    payload['grade'] = children[0].get('grade')
                    payload['school'] = children[0].get('school')

                try:
                    upd = supabase.table('parents').update(payload).eq('id', profile.get('id')).execute()
                    err = getattr(upd, 'error', None)
                    if err is None:
                        st.success('Profile updated successfully.')
                        st.session_state['editing_profile'] = False
                        try:
                            st.experimental_rerun()
                        except Exception:
                            st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                    else:
                        # If the DB doesn't have certain columns (older schema), retry without them
                        try:
                            msg = err.get('message') if isinstance(err, dict) else str(err)
                        except Exception:
                            msg = str(err)

                        # Fallback for missing `email` column
                        if msg and 'email' in msg and ('Could not find' in msg or 'could not find' in msg):
                            fallback = payload.copy()
                            fallback.pop('email', None)
                            try:
                                upd2 = supabase.table('parents').update(fallback).eq('id', profile.get('id')).execute()
                                if getattr(upd2, 'error', None) is None:
                                    st.success("Profile updated (saved without 'email' field; database schema lacks that column).")
                                    st.warning("Database does not have an 'email' column; consider adding it for full functionality.")
                                    st.session_state['editing_profile'] = False
                                    try:
                                        st.experimental_rerun()
                                    except Exception:
                                        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                                else:
                                    st.error(f"Failed to update profile: {getattr(upd2, 'error')}")
                            except Exception as e2:
                                st.error(f"Failed to update profile: {e2}")

                        # Fallback for missing `children` column
                        elif msg and 'children' in msg and ('Could not find' in msg or 'could not find' in msg):
                            fallback = payload.copy()
                            fallback.pop('children', None)
                            try:
                                upd2 = supabase.table('parents').update(fallback).eq('id', profile.get('id')).execute()
                                if getattr(upd2, 'error', None) is None:
                                    st.success("Profile updated (saved without 'children' field; database schema lacks that column).")
                                    st.warning("Database does not have a 'children' column; consider adding it for multi-child support.")
                                    st.session_state['editing_profile'] = False
                                    try:
                                        st.experimental_rerun()
                                    except Exception:
                                        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                                else:
                                    st.error(f"Failed to update profile: {getattr(upd2, 'error')}")
                            except Exception as e2:
                                st.error(f"Failed to update profile: {e2}")
                        else:
                            st.error(f"Failed to update profile: {err}")
                except Exception as e:
                    st.error(f"Failed to update profile: {e}")

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
                    err = getattr(insert_res, 'error', None)
                    # If DB lacks `email` column, retry without it
                    try:
                        msg = err.get('message') if isinstance(err, dict) else str(err)
                    except Exception:
                        msg = str(err)

                    if msg and 'email' in msg and ('Could not find' in msg or 'could not find' in msg):
                        fallback = payload.copy()
                        fallback.pop('email', None)
                        try:
                            retry = supabase.table('parents').insert(fallback).execute()
                            if getattr(retry, 'error', None) is None and getattr(retry, 'data', None):
                                st.success("Profile saved (without 'email' field; database schema lacks that column).")
                                st.warning("Database does not have an 'email' column; consider adding it for full functionality.")
                                try:
                                    st.experimental_rerun()
                                except Exception:
                                    st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)
                            else:
                                st.error(f"Failed to save profile. Error: {getattr(retry, 'error', None)}")
                        except Exception as e2:
                            st.error(f"Failed to save profile: {e2}")
                    else:
                        st.error(f"Failed to save profile. Error: {err}")
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
