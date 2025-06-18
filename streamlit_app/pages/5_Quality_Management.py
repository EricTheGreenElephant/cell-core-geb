import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.quality_management.product_qm_review_form import render_product_qm_review
from components.quality_management.audit_log_view import render_audit_log_view
from components.common.toggle import toggle_button

if "view_product_qm" not in st.session_state: 
    st.session_state.view_product_qm = False
if "view_audit_log" not in st.session_state:
    st.session_state.view_audit_log = False

st.title("Quality Management")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Quality Management", minimum_level="Write")

# --- Page structure ---
tab1, tab2 = st.tabs(["QM Approval", "Audit Logs"])

with tab1:
    toggle_button("view_product_qm", "Get Products", "Hide Products")
    if st.session_state.get("view_product_qm", False):
        render_product_qm_review()

with tab2:
    toggle_button("view_audit_log", "Show Audit Log", "Hide Audit Log")
    if st.session_state.get("view_audit_log", False):
        render_audit_log_view()