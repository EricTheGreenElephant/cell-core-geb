import streamlit as st
from components.lids_seals.lids_seals_inventory_form import render_lids_seals_inventory
from components.lids_seals.lids_seals_add_form import render_add_lid_seal_form
from components.lids_seals.lids_edit_form import render_edit_lid_form
from components.common.toggle import toggle_button
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar


OPTIONS = ["Select an option...", "Lid", "Seal"]

if "show_lid_inventory" not in st.session_state:
    st.session_state.show_lid_inventory = False

if "add_lid_batch" not in st.session_state:
    st.session_state.add_lid_batch = False

if "edit_lid_batch" not in st.session_state:
    st.session_state.edit_lid_batch = False

st.title("Lids and Seals")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
user_level = require_access("Logistics", minimum_level="Read")

# --- Page structure ---
tab1, tab2, tab3 = st.tabs(["Inventory", "Enter Batch", "Edit Batch"])

with tab1:
    # toggle_button("show_lid_inventory", "Show Lid Inventory", "Hide Lid Inventory")
    # if st.session_state.get("show_lid_inventory", False):
    mode = st.selectbox("Choose inventory:", options=OPTIONS, index=0, key="ls_inv_mode")
    if mode != OPTIONS[0]:
        render_lids_seals_inventory(mode)

with tab2:
    if user_level in ("Write", "Admin"):
        mode = st.selectbox("Choose batch type:", options=OPTIONS, index=0, key="ls_add_mode")
        # toggle_button("add_lid_batch", "Add Lid Batch", "Hide Lid Batch")
        # if st.session_state.get("add_lid_batch", False):
        if mode != OPTIONS[0]:
            render_add_lid_seal_form(mode)

with tab3:
    if user_level in ("Write", "Admin"):
        # toggle_button("edit_lid_batch", "Edit Lid Batch", "Hide Edit")
        # if st.session_state.get("edit_lid_batch", False):
        mode = st.selectbox("Choose edit form:", options=OPTIONS, index=0, key="ls_edit_mode")
        if mode != OPTIONS[0]:
            render_edit_lid_form(mode)
