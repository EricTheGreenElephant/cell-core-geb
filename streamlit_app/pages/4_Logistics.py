import streamlit as st
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.logistics.logistics_form import render_logistics_form
from components.logistics.storage_assignment_form import render_storage_assignment_form
from components.logistics.treatment_qc_form import render_treatment_qc_form
from components.common.toggle import toggle_button


if "create_batch" not in st.session_state:
    st.session_state.create_batch = False

if "assign_storage" not in st.session_state:
    st.session_state.assign_storage = False

if "show_treatment_qc" not in st.session_state:
    st.session_state.show_treatment_qc = False

st.title("Logistics & Treatment Dispatch")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Logistics", "Write")

# --- Page structure ---
tab1, tab2, tab3 = st.tabs(["Harvest Storage", "Treatment Batch", "Treatment QC"])

with tab1:
    toggle_button("assign_storage", "Assign Storage", "Hide Storage")
    if st.session_state.get("assign_storage", False):
        render_storage_assignment_form()

with tab2:
    toggle_button("create_batch", "Create Treatment Batch", "Hide Treatment Batch")
    if st.session_state.get("create_batch", False):
        render_logistics_form()
    
with tab3:
    toggle_button("show_treatment_qc", "Show QC Requests", "Hide QC Requests")
    if st.session_state.get("show_treatment_qc", False):
        render_treatment_qc_form()