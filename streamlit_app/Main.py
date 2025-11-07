# # import streamlit as st
# # import json
# # from utils.auth import show_user_sidebar
# # from components.common.login_widget import login_widget

# # If user is logged in, show welcome message
# # if "user_id" in st.session_state:
# #     st.success(f"Welcome, {st.session_state.display_name}")
# #     st.markdown("Use the sidebar to navigate to an area of the application.")
# #     show_user_sidebar()


# # Main.py
# import streamlit as st
# from streamlit_js_eval import streamlit_js_eval
# import os
# import json
# import requests
# from streamlit.components.v1 import iframe
# from components.common.login_widget import login_widget, debug_auth_panel
# from utils.auth import authenticate_principal, _extract_identity



# col_sp, col_login, col_logout = st.columns([1, 0.15, 0.15])
# with col_login:
#     st.link_button("🔐 Login",  f"{base}/.auth/login/aad?post_login_redirect_uri=/", width="stretch")
# with col_logout:
#     st.link_button("🚪 Logout", f"{base}/.auth/logout?post_logout_redirect_uri=/", width="stretch")

# st.write("If the app is really authenticated, this box should show your JSON *inside* the app:")
# iframe(f"{base}/.auth/me", height=220)



# # (Login/Logout buttons already added at the very top per step 1)

# # Run the login flow
# # login_widget()

# # TEMP: show what the app actually sees (remove later)
# # debug_auth_panel()

# # # Always greet if we have either DB-backed or claims-only identity
# # name  = st.session_state.get("display_name") or st.session_state.get("_principal_name")
# # email = st.session_state.get("_principal_upn")
# # if name or email:
# #     who = name or email or "User"
# #     st.success(f"Welcome, {who}" + (f" ({email})" if email and email != who else ""))
# #     if "access" not in st.session_state:
# #         st.caption("Signed in with Microsoft Entra. App features will appear once database/access is loaded.")
# # else:
# #     st.info("Please sign in to continue.")
# streamlit_app.py
import urllib.parse
import streamlit as st
from utils.auth import get_current_user

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")

# 1️ Define helper functions here (login_url, logout_url, etc.)
def _current_path_with_query():
    qs = st.query_params
    q = urllib.parse.urlencode(qs, doseq=True)
    return (st.context.request.path or "/") + (f"?{q}" if q else "")

def login_url():
    return "/.auth/login/aad?post_login_redirect_uri=" + urllib.parse.quote(_current_path_with_query(), safe="")

def logout_url(redirect_to: str = "/"):
    return "/.auth/logout?post_logout_redirect_uri=" + urllib.parse.quote(redirect_to, safe="")

# 2️ Read the current signed-in user (using your auth.py)
user = get_current_user()

# 3️ Add the login/logout controls in your sidebar
with st.sidebar.expander("Account", expanded=True):
    if user:
        st.write(f"Signed in as **{user['name'] or user['email']}**")
        cols = st.columns([1, 1])
        with cols[0]:
            st.link_button("Log out", logout_url("/"))  # Return to home
        with cols[1]:
            st.link_button("Switch account", logout_url(login_url()))
    else:
        st.write("You’re not signed in.")
        st.link_button("Log in", login_url())
        st.caption("Use your Microsoft Entra account.")

# 4️ Require authentication for the main content
if not user:
    st.stop()

# 5️ App content (only runs if signed in)
st.title("CellCore")
st.write(f"Welcome, **{user['name'] or user['email'] or 'friend'}**!")

# Example: simple authorization gate by Entra Object ID (best practice)
ALLOWED_OIDS = {"158bee0b-b61b-40d2-b83f-b0ac897e7659"}  # replace with real OIDs
if user["oid"] not in ALLOWED_OIDS:
    st.error("You don’t have access to this page.")
    st.stop()

st.success("You are authorized 🎉")
# …rest of your app
