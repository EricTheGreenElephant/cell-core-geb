import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.qc_form import render_qc_form


require_login()
require_access("Quality Control", minimum_level="Write")
show_user_sidebar()

st.title("Quality Management")

tab1, tab2 = st.tabs(["Product QC", "Treatment QC"])

with tab1:
    render_qc_form()