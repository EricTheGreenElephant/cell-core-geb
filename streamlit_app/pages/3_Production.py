import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.status_tracker import render_status_tracker
from components.request_form import render_product_request_form
from components.harvest_form import render_harvest_form
from components.qc_form import render_qc_form


st.title("Production Management")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Production", minimum_level="Read")

# Get user's access level
access_level = st.session_state["access"]["Production"]

# --- Page structure ---
tab1, tab2, tab3, tab4 = st.tabs(["Inventory", "New Request", "Harvest Requests", "Product QC"])

with tab1:
    render_status_tracker()

with tab2:
    if access_level in ("Write", "Admin"):
        render_product_request_form()
    else:
        st.warning("🔒 You do not have permission to view Requests.")

with tab3:
    if access_level in ("Write", "Admin"):
        render_harvest_form()
    else:
        st.warning("🔒 You do not have permission to view Harvest Requests.")

with tab4:
    if access_level in ("Write", "Admin"):
        render_qc_form()
    else:
        st.warning("🔒 You do not have permission to view Product QC")