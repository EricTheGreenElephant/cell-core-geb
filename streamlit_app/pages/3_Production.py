import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.production.status_tracker import render_status_tracker
from components.production.request_form import render_product_request_form
from components.production.harvest_form import render_harvest_form
from components.production.harvest_edit_form import render_harvest_edit_form
from components.production.harvest_undo_form import render_harvest_undo_form
from components.logistics.qc_form import render_qc_form
from components.logistics.qc_edit_form import render_qc_edit_form
from components.common.toggle import toggle_button


if "show_inventory" not in st.session_state:
    st.session_state.show_inventory = False

if "create_requests" not in st.session_state:
    st.session_state.create_requests = False

if "show_requests" not in st.session_state:
    st.session_state.show_requests = False

if "show_qc_requests" not in st.session_state:
    st.session_state.show_qc_requests = False

st.title("Production Management")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Production", minimum_level="Read")

# Get user's access level
access_level = st.session_state["access"]["Production"]

# --- Page structure ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Inventory", "New Request", "Harvest Requests", "Product QC", "Edit Products"])

with tab1:
    toggle_button("show_inventory", "Show Inventory", "Hide Inventory")
    if st.session_state.get("show_inventory", False):
        render_status_tracker()

with tab2:
    if access_level in ("Write", "Admin"):
        toggle_button("create_requests", "Create Requests", "Hide Requests")
        if st.session_state.get("create_requests", False):
            render_product_request_form()
    else:
        st.warning("🔒 You do not have permission to view Requests.")

with tab3:
    if access_level in ("Write", "Admin"):
        toggle_button("show_requests", "Retrieve Requests", "Hide Requests")
        if st.session_state.get("show_requests", False):
            render_harvest_form()
    else:
        st.warning("🔒 You do not have permission to view Harvest Requests.")

with tab4:
    if access_level in ("Write", "Admin"):
        toggle_button("show_qc_requests", "Retrieve QC Requests", "Hide QC Requests")
        if st.session_state.get("show_qc_requests", False):
            render_qc_form()
    else:
        st.warning("🔒 You do not have permission to view Product QC")

with tab5:
    if access_level in ("Write", "Admin"):
        toggle = st.selectbox(
            label="Edit Data",
            options=["Select an option...", "Undo Harvest", "Edit Harvest Data", "Edit QC Data"],
            index=0 
        )
        match toggle:
            case "Undo Harvest":
                render_harvest_undo_form()
            case "Edit Harvest Data":
                render_harvest_edit_form()
            case "Edit QC Data":
                render_qc_edit_form()