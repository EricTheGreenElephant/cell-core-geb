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
from components.common.login_widget import login_widget, debug_auth_panel

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")
st.title("CellCore")

# (Login/Logout buttons already added at the very top per step 1)

# Run the login flow
login_widget()

# TEMP: show what the app actually sees (remove later)
debug_auth_panel()

# Always greet if we have either DB-backed or claims-only identity
name  = st.session_state.get("display_name") or st.session_state.get("_principal_name")
email = st.session_state.get("_principal_upn")
if name or email:
    who = name or email or "User"
    st.success(f"Welcome, {who}" + (f" ({email})" if email and email != who else ""))
    if "access" not in st.session_state:
        st.caption("Signed in with Microsoft Entra. App features will appear once database/access is loaded.")
else:
    st.info("Please sign in to continue.")
