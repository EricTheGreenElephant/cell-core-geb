import streamlit as st
from components.lids.lids_inventory_form import render_lid_inventory
from components.lids.lids_add_form import render_add_lid_form
from components.lids.lids_edit_form import render_edit_lid_form
from components.common.toggle import toggle_button
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar


if "show_lid_inventory" not in st.session_state:
    st.session_state.show_lid_inventory = False

if "add_lid_batch" not in st.session_state:
    st.session_state.add_lid_batch = False

if "edit_lid_batch" not in st.session_state:
    st.session_state.edit_lid_batch = False

st.title("Lids")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
user_level = require_access("Logistics", minimum_level="Read")

# --- Page structure ---
tab1, tab2, tab3 = st.tabs(["Inventory", "Enter Lid Batch", "Enter Lid Batch"])

with tab1:
    toggle_button("show_lid_inventory", "Show Lid Inventory", "Hide Lid Inventory")
    if st.session_state.get("show_lid_inventory", False):
        render_lid_inventory()

with tab2:
    if user_level in ("Write", "Admin"):
        toggle_button("add_lid_batch", "Add Lid Batch", "Hide Lid Batch")
        if st.session_state.get("add_lid_batch", False):
            render_add_lid_form()

with tab3:
    if user_level in ("Write", "Admin"):
        toggle_button("edit_lid_batch", "Edit Lid Batch", "Hide Edit")
        if st.session_state.get("edit_lid_batch", False):
            render_edit_lid_form()
