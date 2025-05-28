import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.common.admin_record_lookup import render_admin_record_lookup
from components.common.toggle import toggle_button


if "retrieve_record" not in st.session_state:
    st.session_state.retrieve_record = False

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("Admin Dashboard")

# Show user info and logout
show_user_sidebar()

# --- Access Control ---
require_login()
access_level = require_access("Admin Dashboard", minimum_level="Admin")

toggle_button("retrieve_record", "Search Record", "Hide Record")
if st.session_state.get("retrieve_record", False):
    render_admin_record_lookup()