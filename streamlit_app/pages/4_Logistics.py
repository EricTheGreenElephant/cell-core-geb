import streamlit as st
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.logistics_form import render_logistics_form
from components.harvest_storage_form import render_harvest_storage_form
from components.toggle import toggle_button


if "create_batch" not in st.session_state:
    st.session_state.create_batch = False

st.title("Logistics & Treatment Dispatch")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Logistics", "Write")

# --- Page structure ---
tab1, tab2, tab3 = st.tabs(["Harvest Storage", "Treatment Batch", "Treatment QC"])

with tab1:
    render_harvest_storage_form()

with tab2:
    toggle_button("create_batch", "Create Treatment Batch", "Hide Treatment Batch")
    if st.session_state.get("create_batch", False):
        render_logistics_form()
    
with tab3:
    st.markdown("Currently Under Construction")