import streamlit as st
from utils.session import require_login, require_access
# from utils.auth import show_user_sidebar
from components.quality_management.product_qm_review_form import render_product_qm_review
from components.quality_management.quarantine_review_form import render_quarantine_review_form
from components.quality_management.investigation_review_form import render_investigation_review
from components.quality_management.audit_log_view import render_audit_log_view
from components.quality_management.adhoc_quarantine_form import render_ad_hoc_quarantine
from components.common.toggle import toggle_button

if "view_product_qm" not in st.session_state: 
    st.session_state.view_product_qm = False
if "view_audit_log" not in st.session_state:
    st.session_state.view_audit_log = False
if "view_quarantined_products" not in st.session_state:
    st.session_state.view_quarantined_products = False

st.title("Quality Management")

# --- User logout ---
# show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Quality Management", minimum_level="Write")

# --- Page structure ---
tab1, tab2, tab3 = st.tabs(["QM Approval", "Quarantine Review", "Audit Logs"])

with tab1:
    toggle_button("view_product_qm", "Get Products", "Hide Products")
    if st.session_state.get("view_product_qm", False):
        render_product_qm_review()

with tab2:
    # toggle_button("view_quarantined_products", "Review Quarantined Products", "Hide Products")
    # if st.session_state.get("view_quarantined_products", False):
    review_mode = st.selectbox(
        "Choose Review Option",
        options=["Select an option...", "Quarantine Review", "Under Investigation", "Ad-Hoc Quarantine"],
        key="review_mode_select"
    )
    if review_mode == "Quarantine Review":
        render_quarantine_review_form()
    elif review_mode == "Under Investigation":
        render_investigation_review()
    elif review_mode == "Ad-Hoc Quarantine":
        render_ad_hoc_quarantine()
with tab3:
    toggle_button("view_audit_log", "Show Audit Log", "Hide Audit Log")
    if st.session_state.get("view_audit_log", False):
        render_audit_log_view()