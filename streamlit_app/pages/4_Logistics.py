import streamlit as st
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.logistics.logistics_form import render_logistics_form
from components.logistics.storage_assignment_form import render_storage_assignment_form
from components.logistics.storage_audit import render_shelf_stage_mismatch_report
from components.logistics.treatment_qc_form import render_treatment_qc_form
from components.logistics.storage_edit_form import render_storage_edit_form
from components.logistics.treatment_qc_edit_form import render_treatment_qc_edit_form
from components.logistics.treatment_batch_edit_form import render_treatment_batch_edit_form
from components.logistics.sales_inventory_form import render_sales_tab
from components.logistics.sales_batch_form import render_sales_batch_form
from components.logistics.expiration_review_form import render_expiration_review
from components.common.toggle import toggle_button


if "create_batch" not in st.session_state:
    st.session_state.create_batch = False

if "assign_storage" not in st.session_state:
    st.session_state.assign_storage = False

if "show_treatment_qc" not in st.session_state:
    st.session_state.show_treatment_qc = False

if "check_expired" not in st.session_state:
    st.session_state.check_expired = False

st.title("Logistics & Treatment Dispatch")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Logistics", "Write")

# --- Page structure ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Storage", "Treatment Batch", "Treatment QC", "Sales Batch", "Expired Products", "Edit Storage and Treatment"])

with tab1:
    toggle_storage = st.selectbox(
        label="Select Storage Option",
        options=["Select an option...", "Assign Storage", "Check Mismatched Inventory"],
        index=0
    )

    if toggle_storage == "Assign Storage":
        render_storage_assignment_form()
    
    elif toggle_storage == "Check Mismatched Inventory":
        render_shelf_stage_mismatch_report()

with tab2:
    toggle_button("create_batch", "Create Treatment Batch", "Hide Treatment Batch")
    if st.session_state.get("create_batch", False):
        render_logistics_form()
    
with tab3:
    toggle_button("show_treatment_qc", "Show QC Requests", "Hide QC Requests")
    if st.session_state.get("show_treatment_qc", False):
        render_treatment_qc_form()

with tab4:
    toggle = st.selectbox(
        label="Choose Option",
        options=["Select an option...", "View Sales Inventory", "Create Sales Batch"],
        index=0,
    )
    if toggle == "View Sales Inventory":
        render_sales_tab()
    
    elif toggle == "Create Sales Batch":
        render_sales_batch_form()

with tab5:
    toggle_button("check_expired", "Check Expired Products", "Hide Expired Products")
    if st.session_state.get("check_expired", False):
        render_expiration_review()

with tab6:
    toggle = st.selectbox(
        label="Edit Data", 
        options=["Select an option...", "Edit Storage", "Edit Treatment Batch", "Edit QC Data"],
        index=0
    )
    match toggle:
        case "Edit Storage":
            render_storage_edit_form()
        case "Edit Treatment Batch":
            render_treatment_batch_edit_form()
        case "Edit QC Data":
            render_treatment_qc_edit_form()