import streamlit as st

# Prefer server-side query params
try:
    qp = st.query_params or {}
except Exception:
    qp = {}

access_token = None
for key in ("access_token", "token", "token_hash"):
    if qp.get(key):
        access_token = qp[key][0]
        break

# If not found server-side (very rare after the homepage conversion), inject JS to
# extract from fragment and post it back to Streamlit via window.location
if not access_token:
    try:
        st.markdown(
            """
            <script>
            (function() {
              try {
                const hash = window.location.hash || "";
                if (!hash) return;
                const params = new URLSearchParams(hash.slice(1));
                const type = params.get("type");
                const access_token = params.get("access_token") || params.get("token") || params.get("token_hash");
                if (type === "recovery" && access_token) {
                  // Build a query string with token, plus a marker to avoid loops
                  const q = new URLSearchParams(window.location.search);
                  q.set("type", type);
                  q.set("access_token", access_token);
                  q.set("from_fragment", "1");
                  const newUrl = window.location.origin + window.location.pathname + "?" + q.toString();
                  window.location.replace(newUrl);
                }
              } catch (e) {
                console.error(e);
              }
            })();
            </script>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    st.stop()

# Now access_token is available

# Store token into session state for use by the UI and avoid exposing it in
# query params. Then attempt to clear query params so the token isn't visible.
try:
    if access_token:
        st.session_state['tp_recovery_token'] = access_token
    try:
        # Clear sensitive query params from URL (this triggers a reload)
        # Replaced deprecated API: use `st.query_params` getter; setting
        # query params isn't available without experimental API in some
        # Streamlit versions — clear by setting empty dict via the
        # recommended API if available.
        try:
            st.experimental_set_query_params()
        except Exception:
            # Best-effort: assign to st.session_state marker and continue
            pass
    except Exception:
        pass
except Exception:
    pass

# Continue with your password reset UI/logic
st.write("Proceeding with password reset...")
try:
    st.markdown("<div style='font-size:12px;color:#666'>Debug: recovery token present</div>", unsafe_allow_html=True)
except Exception:
    pass

# Example: show a form to set a new password, then call Supabase to complete the recovery.
# Use access_token in whatever API call you need.
token = access_token or st.session_state.get('tp_recovery_token')

if not token:
    st.error('No recovery token found. Open the password recovery link from your email.')
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
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            resp = _httpx.put(url, json={'password': new_pw}, headers=headers, timeout=10.0)
            if resp.status_code in (200, 204):
                st.success('Password updated. You will be redirected to the login page...')
                # Clear token from session state
                try:
                    if 'tp_recovery_token' in st.session_state:
                        del st.session_state['tp_recovery_token']
                except Exception:
                    pass
                try:
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
