import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar


st.title("Quality Management")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Quality Control", minimum_level="Write")

# --- Page structure ---
tab1, tab2 = st.tabs(["Product QM", "Treatment QM"])

with tab1:
    st.markdown("Currently Under Construction")

with tab2:
    st.markdown("Currently Under Construction")