import streamlit as st
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.logistics_form import render_logistics_form


st.title("Logistics & Treatment Dispatch")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Logistics", "Write")

# --- Page structure ---
tab1, tab2, tab3 = st.tabs(["Harvest Storage", "Treatment Batch", "Treatment QC"])

with tab1:
    st.markdown("Currently Under Construction")

with tab2:
    st.markdown("Currently Under Construction")
    
with tab3:
    render_logistics_form()