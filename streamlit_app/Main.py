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
from streamlit_js_eval import streamlit_js_eval
import os
import json
import requests
from streamlit.components.v1 import iframe
from components.common.login_widget import login_widget, debug_auth_panel
from utils.auth import authenticate_principal, _extract_identity

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")
st.title("CellCore Production")


host = os.environ.get("WEBSITE_HOSTNAME", "").strip()
st.caption(host)
base = f"https://{host}" if host else "https://cellcore-streamlit-web.azurewebsites.net"

st.caption(f"Host: {host or 'cellcore-streamlit-web.azurewebsites.net'}")


col_sp, col_login, col_logout = st.columns([1, 0.15, 0.15])
with col_login:
    st.link_button("🔐 Login",  f"{base}/.auth/login/aad?post_login_redirect_uri=/", width="stretch")
with col_logout:
    st.link_button("🚪 Logout", f"{base}/.auth/logout?post_logout_redirect_uri=/", width="stretch")


def _get_appservice_auth_cookie() -> str | None:
    """
    Reads the App Service auth cookie from the browser and returns its value.
    Cookie names can vary, so we scan for the one that starts with 'AppServiceAuthSession'.
    """
    cookie_str = streamlit_js_eval(js_code="return document.cookie;", key="cookie_scan_v1")
    if not cookie_str:
        return None
    # Find the auth cookie (there may be multiple with chunk suffixes)
    parts = [p.strip() for p in cookie_str.split(";")]
    auth_cookies = [p for p in parts if p.startswith("AppServiceAuthSession")]
    if not auth_cookies:
        return None
    # Join all chunks if present
    # Example chunked names: AppServiceAuthSession, AppServiceAuthSession_0, _1, ...
    # We’ll send all in the Cookie header to be safe.
    return "; ".join(auth_cookies)

@st.cache_data(show_spinner=False)
def _get_principal_via_server(cookie_header: str | None) -> dict | None:
    """
    Server-side GET to /.auth/me using the auth cookie captured from the browser.
    """
    if not cookie_header:
        return None
    try:
        resp = requests.get(f"{base}/.auth/me",
                            headers={"Cookie": cookie_header, "Cache-Control": "no-store"},
                            timeout=5)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None

cookie_header = _get_appservice_auth_cookie()
principal = _get_principal_via_server(cookie_header)

# Debug (remove later)
with st.expander("Debug • principal (server fetch with browser cookie)"):
    st.code(json.dumps(principal, indent=2) if principal else "No principal")

if principal:
    oid, upn, display_name, groups = _extract_identity(principal)
    name = display_name or (upn.split("@")[0] if upn else "User")
    st.success(f"Welcome, {name}" + (f" ({upn})" if upn else ""))

    # Optional: try DB-backed auth to populate access
    try:
        ok, msg = authenticate_principal(principal, mode="autoprovision")
        if ok:
            st.caption("Access loaded from database.")
    except Exception:
        st.caption("Signed in via Microsoft. Database not connected/seeded yet, so access is limited.")
else:
    st.info("If you aren’t redirected automatically, click Login above.")


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
