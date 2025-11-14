import streamlit as st
from components.lids_seals.lids_seals_inventory_form import render_lids_seals_inventory
from components.lids_seals.lids_seals_add_form import render_add_lid_seal_form
from components.lids_seals.lids_seals_edit_form import render_edit_lid_form
from utils.session import require_access, require_login
# from utils.auth import show_user_sidebar


OPTIONS = ["Select an option...", "Lid", "Seal"]

st.title("Lids and Seals")

# --- User logout ---
# show_user_sidebar()

# --- Login Check ---
require_login()
user_level = require_access("Logistics", minimum_level="Read")

# --- Page structure ---
tab1, tab2, tab3 = st.tabs(["Inventory", "Enter Batch", "Edit Batch"])

with tab1:
    mode = st.selectbox("Choose inventory:", options=OPTIONS, index=0, key="ls_inv_mode")
    if mode != OPTIONS[0]:
        render_lids_seals_inventory(mode)

with tab2:
    if user_level in ("Write", "Admin"):
        mode = st.selectbox("Choose batch type:", options=OPTIONS, index=0, key="ls_add_mode")
        if mode != OPTIONS[0]:
            render_add_lid_seal_form(mode)

with tab3:
    if user_level in ("Write", "Admin"):
        mode = st.selectbox("Choose edit form:", options=OPTIONS, index=0, key="ls_edit_mode")
        if mode != OPTIONS[0]:
            render_edit_lid_form(mode)
