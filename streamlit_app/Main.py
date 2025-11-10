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

import streamlit as st
from utils.auth import get_current_user
from utils.auth_ui import render_account_box

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")

render_account_box(expanded=True, home_after_logout="/")

user = get_current_user()

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

from utils.db import run_query

st.header("Database Connection Test")

if st.button("Test Database Connection"):
    try:
        rows = run_query("SELECT TOP (5) name, create_date FROM sys.tables ORDER BY create_date DESC;")
        st.success("✅ Connected successfully using Managed Identity!")
        st.write("Here are some tables SQL sees:")
        st.table(rows)
    except Exception as e:
        st.error(f"❌ Database connection failed:\n\n{e}")
# …rest of your app
