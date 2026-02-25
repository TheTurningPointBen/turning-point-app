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
        # Ensure dispatcher keeps rendering the password_reset page when
        # we clear query params (clearing causes a reload which might
        # otherwise land on the homepage). Set the page explicitly and
        # rerun after clearing.
        try:
            st.session_state['page'] = 'password_reset'
        except Exception:
            pass
        try:
            # Attempt to clear query params. If available, this reloads
            # the page; we set `page` above to keep rendering here.
            st.experimental_set_query_params()
            try:
                st.experimental_rerun()
            except Exception:
                pass
        except Exception:
            # If clearing isn't available, continue without it.
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
        try:
            # Prefer using the configured Supabase client so we reuse existing
            # HTTP settings and avoid managing raw tokens manually.
            from utils.database import supabase

            # Try to set the session with the recovery access token so the
            # client has the correct auth context for update_user.
            try:
                # Newer supabase-py accepts a dict; older signatures accept kwargs.
                try:
                    supabase.auth.set_session({"access_token": token, "refresh_token": None})
                except Exception:
                    supabase.auth.set_session(access_token=token, refresh_token=None)
            except Exception:
                # If we cannot set the session that's ok — we can still attempt
                # to call update_user with the provided token in some clients.
                pass

            # Attempt to update the user's password via the client API.
            try:
                res = supabase.auth.update_user({"password": new_pw})
            except Exception:
                # Some client versions return a (data, error) tuple or a dict.
                try:
                    res = supabase.auth.api.update_user(token, {"password": new_pw})
                except Exception as e:
                    res = {"error": str(e)}

            # Interpret result: accept truthy result with no error field, or
            # a dict where 'error' is falsy.
            ok = False
            try:
                if isinstance(res, dict):
                    if not res.get("error"):
                        ok = True
                elif isinstance(res, tuple) and len(res) >= 2:
                    data, error = res[0], res[1]
                    if not error:
                        ok = True
                else:
                    # Fallback: treat any truthy response as success
                    ok = bool(res)
            except Exception:
                ok = False

            if ok:
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
                    # Show structured error when available.
                    if isinstance(res, dict) and res.get("error"):
                        st.error(f"Failed to update password: {res.get('error')}")
                    else:
                        st.error('Failed to update password. See logs for details.')
                except Exception:
                    st.error('Failed to update password. See logs for details.')
        except Exception as e:
            st.error(f'Error while updating password: {e}')
