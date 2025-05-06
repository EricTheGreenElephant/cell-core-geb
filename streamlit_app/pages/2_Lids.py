import streamlit as st
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar


st.title("Lids")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Logistics", "Write")

# --- Page structure ---
tab1, tab2 = st.tabs(["Inventory", "Enter Lid Batch"])

with tab1:
    st.markdown("Currently Under Construction")

with tab2:
    st.markdown("Currently Under Construction")