import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Tutor Profile")
except Exception:
    pass
from utils.database import supabase

st.title("My Tutor Profile")

if "user" not in st.session_state:
    st.warning("Please login first.")
    try:
        st.switch_page("pages/tutor_login.py")
    except Exception:
        st.stop()

user = st.session_state.user

# fetch tutor profile
profile_res = supabase.table("tutors").select("*").eq("user_id", user.id).execute()
profile = profile_res.data[0] if profile_res.data else None

# Top-left Back button (smaller) and spacer
back_col, main_col = st.columns([1, 9])
with back_col:
    if st.button("⬅️ Back", key="back_to_tutor_dashboard_profile"):
        try:
            st.switch_page("pages/tutor.py")
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass

    st.markdown(
        """
        <style>
        .tutor-back-space{height:4px}
        </style>
        <div class="tutor-back-space"></div>
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

if not profile:
    st.subheader("Complete Your Tutor Profile")
    name = st.text_input("Name")
    surname = st.text_input("Surname")
    phone = st.text_input("Phone Number")
    town = st.text_input("Town")
    city = st.text_input("City")
    email = st.text_input("Email", value=getattr(user, 'email', '') or "")
    st.markdown("---")
    st.subheader("Languages")
    st.info("All exams you currently will Read or Scribe will be in English.\nPlease choose languages below that you can also Read and Scribe in proficiently. Leave blank if none apply.")
    afrikaans = st.checkbox("Afrikaans")
    isizulu = st.checkbox("IsiZulu")
    setswana = st.checkbox("Setswana")
    isixhosa = st.checkbox("IsiXhosa")
    french = st.checkbox("French")

    roles_options = ["Reader", "Scribe", "Both (Reader & Scribe)", "Invigilator", "Prompter", "All of the Above"]
    roles = st.selectbox("Role", roles_options)
    st.markdown("---")
    st.subheader("Transport")
    transport = st.checkbox("I have my own transport")

    if st.button("Save Profile"):
        if not all([name, surname, phone, town, city, email]):
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
                    "email": email,
                    "transport": transport,
                    "roles": roles,
                    "afrikaans": bool(afrikaans),
                    "isizulu": bool(isizulu),
                    "setswana": bool(setswana),
                    "isixhosa": bool(isixhosa),
                    "french": bool(french)
                }).execute()

                if getattr(insert_res, 'error', None) is None:
                    st.success("Profile submitted. Await admin approval.")
                    safe_rerun()
                else:
                    st.error(f"Failed to submit profile: {getattr(insert_res, 'error', None)}")
            except Exception as e:
                st.error(f"Submission error: {e}")
    st.stop()

# Show profile and allow limited edits if approved state exists
st.subheader("Profile Details")
st.write(f"**Name:** {profile.get('name')} {profile.get('surname')}")
st.write(f"**Email:** {profile.get('email') or getattr(user, 'email', '')}")
st.write(f"**Phone:** {profile.get('phone')}")
st.write(f"**Town / City:** {profile.get('town')} / {profile.get('city')}")
st.write(f"**Transport:** {'Yes' if profile.get('transport') else 'No'}")
st.write(f"**Roles:** {profile.get('roles')}")
st.write(f"**Approved:** {profile.get('approved')}")

# Languages display: English is the default; show any additional selected languages
langs = []
if profile.get('afrikaans'):
    langs.append('Afrikaans')
if profile.get('isizulu'):
    langs.append('IsiZulu')
if profile.get('setswana'):
    langs.append('Setswana')
if profile.get('isixhosa'):
    langs.append('IsiXhosa')
if profile.get('french'):
    langs.append('French')

if langs:
    st.write(f"**Languages:** English; {', '.join(langs)}")
else:
    st.write("**Languages:** English")

if st.button("Edit Profile"):
    try:
        st.session_state._editing_tutor_profile = True
        st.experimental_rerun()
    except Exception:
        st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)

if st.session_state.get("_editing_tutor_profile"):
    st.subheader("Edit Profile")
    name = st.text_input("Name", value=profile.get('name') or "")
    surname = st.text_input("Surname", value=profile.get('surname') or "")
    phone = st.text_input("Phone Number", value=profile.get('phone') or "")
    town = st.text_input("Town", value=profile.get('town') or "")
    city = st.text_input("City", value=profile.get('city') or "")
    email = st.text_input("Email", value=profile.get('email') or getattr(user, 'email', '') or "")
    roles_options = ["Reader", "Scribe", "Both (Reader & Scribe)", "Invigilator", "Prompter", "All of the Above"]
    # normalize stored role values that may be 'Both' or 'Both (Reader & Scribe')
    def _normalize_role_label(r):
        if not r:
            return r
        if "Both" in str(r):
            return "Both (Reader & Scribe)"
        return r

    current_role_label = _normalize_role_label(profile.get('roles'))
    roles = st.selectbox("Role", roles_options, index=(roles_options.index(current_role_label) if current_role_label in roles_options else 0))

    st.markdown("---")
    st.subheader("Transport")
    transport = st.checkbox("I have my own transport", value=bool(profile.get('transport')))

    st.markdown("---")
    st.subheader("Languages")
    st.info("All exams you currently will Read or Scribe will be in English.\nPlease choose languages below that you can also Read and Scribe in proficiently. Leave blank if none apply.")
    afrikaans = st.checkbox("Afrikaans", value=bool(profile.get('afrikaans')))
    isizulu = st.checkbox("IsiZulu", value=bool(profile.get('isizulu')))
    setswana = st.checkbox("Setswana", value=bool(profile.get('setswana')))
    isixhosa = st.checkbox("IsiXhosa", value=bool(profile.get('isixhosa')))
    french = st.checkbox("French", value=bool(profile.get('french')))

    if st.button("Save Changes"):
        # Build payload and only include keys that exist in the tutors row
        payload = {}
        existing = set(profile.keys() or [])
        candidates = {
            "name": name,
            "surname": surname,
            "phone": phone,
            "town": town,
            "city": city,
            "email": email,
            "transport": transport,
            "roles": roles,
            "afrikaans": bool(afrikaans),
            "isizulu": bool(isizulu),
            "setswana": bool(setswana),
            "isixhosa": bool(isixhosa),
            "french": bool(french)
        }
        for k, v in candidates.items():
            if k in existing:
                payload[k] = v

        if not payload:
            st.error("No updatable columns found for this tutor in the database.")
        else:
            try:
                update_res = supabase.table("tutors").update(payload).eq("id", profile.get('id')).execute()

                if getattr(update_res, 'error', None) is None:
                    st.success("Profile updated.")
                    del st.session_state["_editing_tutor_profile"]
                    safe_rerun()
                else:
                    st.error(f"Failed to update: {getattr(update_res, 'error', None)}")
            except Exception as e:
                st.error(f"Update error: {e}")