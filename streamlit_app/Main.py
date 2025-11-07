# import streamlit as st
# import json
# from utils.auth import show_user_sidebar
# from components.common.login_widget import login_widget

# st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")
# st.title("CellCore")

# col_sp, col_login, col_logout = st.columns([1, 0.15, 0.15])
# with col_login:
#     st.link_button("Login", "/.auth/login/aad?post_login_redirect_uri=/", width="stretch")
# with col_logout:
#     st.link_button("Logout", "/.auth/logout?post_logout_redirect_uri=/", width="stretch")
# # Show login if not logged in
# login_widget()

# # Prefer DB-authenticated name, fall back to claims-based name
# name = st.session_state.get("display_name") or st.session_state.get("_principal_name")
# email = st.session_state.get("_principal_upn")
# st.write(name)
# st.write(email)
# if name or email:
#     who = name or email or "User"
#     st.success(f"Welcome, {who}" + (f" ({email})" if email and email != who else ""))
#     if "access" not in st.session_state:
#         st.caption("Signed in with Microsoft Entra. App features appear once database/access is loaded.")
# else:
#     st.info("Please sign in to continue.")
# name = st.session_state.get("display_name") or st.session_state.get("_principal_name")
# email = st.session_state.get("_principal_upn")
# if name or email:
#     who = name or email or "User"
#     if email and name:
#         st.success(f"Welcome, {who} ({email})")
#     else:
#         st.success(f"Welcome, {who}")

#     if "access" not in st.session_state:
#         st.caption("You're signed in. Waiting for database/access to be available.")

# If user is logged in, show welcome message
# if "user_id" in st.session_state:
#     st.success(f"Welcome, {st.session_state.display_name}")
#     st.markdown("Use the sidebar to navigate to an area of the application.")
#     show_user_sidebar()


# Main.py
import streamlit as st
from streamlit.components.v1 import iframe, html
import os
import json
from components.common.login_widget import login_widget, debug_auth_panel
from utils.auth import authenticate_principal, _extract_identity

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")
st.title("CellCore")


host = os.environ.get("WEBSITE_HOSTNAME", "").strip()
base = f"https://{host}" if host else "https://cellcore-streamlit-web.azurewebsites.net"

st.caption(f"Host: {host or 'cellcore-streamlit-web.azurewebsites.net'}")


col_sp, col_login, col_logout = st.columns([1, 0.15, 0.15])
with col_login:
    st.link_button("🔐 Login",  f"{base}/.auth/login/aad?post_login_redirect_uri=/", width="stretch")
with col_logout:
    st.link_button("🚪 Logout", f"{base}/.auth/logout?post_logout_redirect_uri=/", width="stretch")


def get_principal_via_iframe_bridge() -> dict | None:
    """
    Reads /.auth/me by loading it into an iframe (same-origin) and
    extracting its body text from the iframe's DOM, then passes it back
    to Streamlit via a hidden <textarea>. No fetch/XHR involved.
    """
    # unique DOM IDs so we don't collide
    iframe_id = "auth_me_iframe"
    sink_id = "auth_me_sink"

    # Render an iframe + JS that pulls the JSON text into a hidden textarea
    html(
        f"""
        <iframe id="{iframe_id}" src="/.auth/me"
                style="display:none"
                sandbox="allow-scripts allow-same-origin"></iframe>

        <script>
          (function() {{
            const f = document.getElementById("{iframe_id}");
            function pull() {{
              try {{
                const doc = f.contentWindow.document;
                // /.auth/me returns JSON; innerText will be the raw JSON string
                const txt = doc && doc.body ? (doc.body.innerText || doc.body.textContent || "") : "";
                const sink = document.getElementById("{sink_id}");
                if (sink && txt) {{
                  sink.value = txt;
                  sink.dispatchEvent(new Event("input", {{ bubbles: true }}));
                }}
              }} catch (e) {{
                // cross-origin or not ready yet; try again
              }}
            }}
            f.addEventListener('load', () => {{
              pull();
              // a couple retries in case content loads after onload
              setTimeout(pull, 200);
              setTimeout(pull, 500);
            }});
          }})();
        </script>

        <textarea id="{sink_id}" style="display:none"></textarea>
        """,
        height=0,
    )

    raw = st.text_area("", key=sink_id, label_visibility="collapsed", height=1)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

# --- use the bridge to get the principal ---
principal = get_principal_via_iframe_bridge()

# TEMP: show what we got (remove later)
with st.expander("Debug • principal (from iframe bridge)"):
    st.code(json.dumps(principal, indent=2) if principal else "No principal")


# If we have a principal, greet; then (optionally) run DB-backed auth
if principal:
    oid, upn, display_name, groups = _extract_identity(principal)

    # Always show welcome from claims (works even if DB is down)
    name = display_name or (upn.split("@")[0] if upn else "User")
    st.success(f"Welcome, {name}" + (f" ({upn})" if upn else ""))

    # Optional: try DB-backed auth now to populate st.session_state.access
    try:
        ok, msg = authenticate_principal(principal, mode="autoprovision")
        if ok:
            st.caption("Access loaded from database.")
    except Exception:
        st.caption("Signed in via Microsoft. Database not connected/seeded yet, so access is limited.")
else:
    st.info("Please click Login above if you’re not redirected automatically.")



st.subheader("Auth check (remove after testing)")
st.write("If the app is really authenticated, this box should show your JSON *inside* the app:")
iframe(f"{base}/.auth/me", height=220)

with st.expander("Use principal from /.auth/me (temporary)"):
    st.caption("Open the iframe above in a new tab, copy ALL the JSON, paste here, click Apply.")
    pasted = st.text_area("Paste JSON from /.auth/me")
    if st.button("Apply principal"):
        try:
            principal = json.loads(pasted)
            # minimal extraction
            claims = (principal[0].get("user_claims", []) if isinstance(principal, list) else principal.get("claims", []))
            cmap = {str(c.get("typ","")).lower(): c.get("val") for c in claims}
            upn  = cmap.get("preferred_username") or cmap.get("upn") or cmap.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress") or cmap.get("emails")
            name = cmap.get("name") or (upn.split("@")[0] if upn else "User")
            st.session_state["_principal_name"] = name
            st.session_state["_principal_upn"] = (upn or "").lower()
            st.success(f"Welcome, {name}" + (f" ({upn})" if upn else ""))
        except Exception as e:
            st.error(f"Could not parse the JSON: {e}")


# (Login/Logout buttons already added at the very top per step 1)

# Run the login flow
# login_widget()

# TEMP: show what the app actually sees (remove later)
# debug_auth_panel()

# # Always greet if we have either DB-backed or claims-only identity
# name  = st.session_state.get("display_name") or st.session_state.get("_principal_name")
# email = st.session_state.get("_principal_upn")
# if name or email:
#     who = name or email or "User"
#     st.success(f"Welcome, {who}" + (f" ({email})" if email and email != who else ""))
#     if "access" not in st.session_state:
#         st.caption("Signed in with Microsoft Entra. App features will appear once database/access is loaded.")
# else:
#     st.info("Please sign in to continue.")
