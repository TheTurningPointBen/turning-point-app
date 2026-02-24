import streamlit as st

# Prefer server-side query params
try:
    qp = st.experimental_get_query_params()
except Exception:
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

# Optionally clear query params so the token is not visible
try:
    # Clear sensitive query params from URL (this triggers a reload)
    st.experimental_set_query_params()
except Exception:
    # If that fails, continue without clearing
    pass

# Continue with your password reset UI/logic
st.write("Proceeding with password reset...")

# Example: show a form to set a new password, then call Supabase to complete the recovery.
# Use access_token in whatever API call you need.

# new_password = st.text_input("New password", type="password")
# if st.button("Reset password"):
#     # perform reset using access_token
#     ...
