import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.status_tracker import render_status_tracker
from components.request_form import render_product_request_form
from components.harvest_form import render_harvest_form

# --- Login Check ---
require_login()
require_access("Production", minimum_level="Read")
show_user_sidebar()

st.title("Production Management")

# Get user's access level
access_level = st.session_state["access"]["Production"]

tab1, tab2, tab3 = st.tabs(["New Request", "Harvest Requests", "Status Tracker"])

with tab1:
    if access_level in ("Write", "Admin"):
        render_product_request_form()
    else:
        st.warning("🔒 You do not have permission to view Requests.")

with tab2:
    if access_level in ("Write", "Admin"):
        render_harvest_form()
    else:
        st.warning("🔒 You do not have permission to view Harvest Requests.")
with tab3:
    render_status_tracker()