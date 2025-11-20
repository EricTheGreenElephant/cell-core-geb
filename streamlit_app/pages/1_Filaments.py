import streamlit as st
from utils.session import require_access, require_login
from utils.auth_ui import render_account_box
# from utils.auth import show_user_sidebar
from components.filaments.filament_form import render_add_filament_form
from components.filaments.filament_mount_form import render_mount_form
from components.filaments.filament_unmount_form import render_unmount_form
from components.filaments.filament_acclimatize_form import render_acclimatizing_form
from components.filaments.filament_health_form import render_health_status
from components.filaments.filament_inventory_form import render_filament_inventory
from components.filaments.restore_mount_form import render_restore_mount_form
from components.filaments.filament_edit_form import render_edit_filament_tab
from components.filaments.filament_mount_edit_form import render_edit_mount_form
from components.filaments.restore_acclimatization_form import render_restore_acclimatization_form
from components.common.toggle import toggle_button


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

if "show_edit_filament_form" not in st.session_state:
    st.session_state.show_edit_filament_form = False

if "show_mount_edit_form" not in st.session_state:
    st.session_state.show_mount_edit_form = False

st.title("🧪Filament Management")

# --- User logout ---
# show_user_sidebar()
render_account_box(expanded=True, home_after_logout="/")

# --- Login check ---
require_login()
user_level = require_access("Logistics", minimum_level="Read")

# --- Page structure ---
tab1, tab2 , tab3, tab4 = st.tabs(["Inventory", "Add Filament", "Service Filament", "Edit Filament"])

with tab1:
    toggle = st.selectbox(
        label="Choose filament view:",
        options=["Select an option...", "View Printer/Filament Status", "View Inventory"],
        index=0
    )
    match toggle:
        case "View Printer/Filament Status":
            render_health_status()
        case "View Inventory":
            render_filament_inventory()

    # # Show individual status
    # toggle_button("show_health_status", "Show Filament Health Status", "Hide Filament Health Status")

    # if st.session_state.get("show_health_status", False):
    #     render_health_status()
    # st.divider()

    # # --- Active Filament Inventory with Filter ---
    # toggle_button("show_active_inventory", "Show Active Filaments", "Hide Active Filaments")
    
    # if st.session_state.get("show_active_inventory", False):
    #     render_filament_inventory()

with tab2: 
    # --- Show Add Form Button ---
    if user_level in ("Write", "Admin"):
        toggle_button("show_add_form", "Add New Filament", "Hide Add Form")

    # --- Show Add Filament Form
    if st.session_state.get("show_add_form", False) and user_level in ("Write", "Admin"):
        render_add_filament_form()

with tab3: 
    if user_level in ("Write", "Admin"):
        toggle = st.selectbox(
            label="Choose Filament Action",
            options=["Select an option...", "Mount Filament", "Unmount Filament", "Move to Acclimatization"],
            index=0
        )
        match toggle:
            case "Mount Filament":
                render_mount_form()
            case "Unmount Filament":
                render_unmount_form()
            case "Move to Acclimatization":
                render_acclimatizing_form()

        # toggle_button("show_mount_form", "Mount Filament", "Hide Mount Form")
        # if st.session_state.get("show_mount_form", False):
        #     render_mount_form()

        # st.divider()
        # toggle_button("show_unmount_form", "Unmount Filament", "Hide Unmount Form")
        # if st.session_state.get("show_unmount_form", False):
        #     render_unmount_form()
        
        # st.divider()
        # toggle_button("show_acclimatize_form", "Move to Acclimatization", "Hide Acclimatization Form")
        # if st.session_state.get("show_acclimatize_form", False):
        #     render_acclimatizing_form()

with tab4:
    if user_level in ("Write", "Admin"):
        toggle = st.selectbox(
            label="Edit Data", 
            options=["Select an option...", "Filament", "Mounted", "Unmounted", "Acclimatization"],
            index=0
        )
        match toggle:
            case "Filament":
                render_edit_filament_tab()
            case "Mounted":
                render_edit_mount_form()
            case "Unmounted":
                render_restore_mount_form()
            case "Acclimatization":
                render_restore_acclimatization_form()
