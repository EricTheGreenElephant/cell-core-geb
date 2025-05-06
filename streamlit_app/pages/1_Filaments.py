import streamlit as st
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.filament_form import render_add_filament_form
from components.filament_mount_form import render_mount_form
from components.filament_unmount_form import render_unmount_form
from components.filament_acclimatize_form import render_acclimatizing_form
from components.filament_health_form import render_health_status
from components.filament_inventory_form import render_filament_inventory
from components.toggle import toggle_button


if "show_active_inventory" not in st.session_state:
    st.session_state.show_active_inventory = False

if "show_health_status" not in st.session_state:
    st.session_state.show_health_status = False

if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False

if "show_unmount_form" not in st.session_state:
    st.session_state.show_unmount_form = False

if "show_acclimatize_form" not in st.session_state:
    st.session_state.show_acclimatize_form = False

st.title("🧪Filament Management")

# --- User logout ---
show_user_sidebar()

# --- Login check ---
require_login()
user_level = require_access("Filament Inventory", minimum_level="Read")

# --- Page structure ---
tab1, tab2 , tab3 = st.tabs(["Inventory", "Add Filament", "Mount Filament"])

with tab1:
    # Show individual status
    toggle_button("show_health_status", "Show Filament Health Status", "Hide Filament Health Status")

    if st.session_state.get("show_health_status", False):
        render_health_status()
    st.divider()

    # --- Active Filament Inventory with Filter ---
    toggle_button("show_active_inventory", "Show Active Filaments", "Hide Active Filaments")
    
    if st.session_state.get("show_active_inventory", False):
        render_filament_inventory()

with tab2: 
    # --- Show Add Form Button ---
    if user_level in ("Write", "Admin"):
        toggle_button("show_add_form", "Add New Filament", "Hide Add Form")

    # --- Show Add Filament Form
    if st.session_state.get("show_add_form", False) and user_level in ("Write", "Admin"):
        render_add_filament_form()

with tab3: 
    if user_level in ("Write", "Admin"):
        toggle_button("show_mount_form", "Mount Filament", "Hide Mount Form")
        if st.session_state.get("show_mount_form", False):
            render_mount_form()

        st.divider()
        toggle_button("show_unmount_form", "Unmount Filament", "Hide Unmount Form")
        if st.session_state.get("show_unmount_form", False):
            render_unmount_form()
        
        st.divider()
        toggle_button("show_acclimatize_form", "Move to Acclimatization", "Hide Acclimatization Form")
        if st.session_state.get("show_acclimatize_form", False):
            render_acclimatizing_form()