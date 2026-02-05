import streamlit as st
from utils.ui import hide_sidebar
hide_sidebar()
try:
    st.set_page_config(page_title="Password Reset")
except Exception:
    pass

st.title('Reset your password')

# If Supabase (or the browser) placed the recovery token in the URL fragment
# (e.g. #access_token=...&type=recovery) the server won't see it. Inject a
# small client-side script to move the fragment into the query string so
# `st.query_params` can observe it.
try:
    st.markdown(
        """
        <script>
        (function(){
            try{
                const params = new URLSearchParams(window.location.search || '');
                if(!params.get('access_token') && window.location.hash){
                    // parse fragment like #access_token=...&type=recovery
                    const frag = window.location.hash.replace(/^#/, '');
                    const fparams = new URLSearchParams(frag);
                    const at = fparams.get('access_token');
                    const t = fparams.get('type');
                        if(at){
                            // build new search preserving any existing params
                            const newParams = new URLSearchParams(window.location.search.replace(/^\?/, ''));
                            if(t) newParams.set('type', t);
                            newParams.set('access_token', at);
                            const newUrl = window.location.pathname + '?' + newParams.toString();
                            // retry replacing the URL for a short window; Streamlit may
                            // overwrite the URL during initialization, so attempt a few
                            // times to ensure the query arrives intact.
                            var doReplace = function(){ try{ history.replaceState(null, '', newUrl); }catch(e){} };
                            doReplace();
                            var iv = setInterval(doReplace, 150);
                            setTimeout(function(){ clearInterval(iv); try{ window.location.href = newUrl; }catch(e){} }, 1200);
                        }
                }
            }catch(e){}
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
except Exception:
    pass

# Read query params
params = {}
try:
    params = st.query_params or {}
except Exception:
    try:
        params = st.query_params or {}
    except Exception:
        params = {}

qp_type = (params.get('type') or [None])[0]
qp_token = (params.get('access_token') or [None])[0]

if qp_type != 'recovery' or not qp_token:
    st.error('This page is intended to be used from the password recovery link sent to your email.')
    st.info('If you requested a password reset, please click the link in the email you received.')
    st.stop()

st.info('Enter a new password for your account.')
new_pw = st.text_input('New password', type='password')
confirm_pw = st.text_input('Confirm password', type='password')

if st.button('Set new password'):
    if not new_pw or new_pw != confirm_pw:
        st.error('Passwords must match and not be empty.')
    else:
        try:
            from config import SUPABASE_URL, SUPABASE_KEY
            import httpx as _httpx

            url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/user"
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {qp_token}',
                'Content-Type': 'application/json'
            }
            resp = _httpx.put(url, json={'password': new_pw}, headers=headers, timeout=10.0)
            if resp.status_code in (200, 204):
                st.success('Password updated. You will be redirected to the login page...')
                try:
                    # Redirect back to the tutor login page so the user can sign in with the new password
                    redirect_js = "<script>setTimeout(function(){ window.location.href='/tutor_login'; }, 1500);</script>"
                    st.markdown(redirect_js, unsafe_allow_html=True)
                except Exception:
                    try:
                        st.markdown("[Go to login](./tutor_login)")
                    except Exception:
                        pass
            else:
                try:
                    st.error(f"Failed to update password: {resp.status_code} {resp.text}")
                except Exception:
                    st.error('Failed to update password. See logs for details.')
        except Exception as e:
            st.error(f'Error while updating password: {e}')
