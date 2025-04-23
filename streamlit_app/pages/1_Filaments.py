import streamlit as st
from data.filament import get_active_filaments, get_archived_filaments, get_in_use_filaments, get_filaments_not_acclimatizing
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.filament_form import render_add_filament_form
from components.filament_mount_form import render_mount_form
from components.filament_unmount_form import render_unmount_form
from components.toggle import toggle_button


if "show_active_inventory" not in st.session_state:
    st.session_state.show_active_inventory = False

if "show_in_use_inventory" not in st.session_state:
    st.session_state.show_in_use_inventory = False

if "show_archived_inventory" not in st.session_state:
    st.session_state.show_archived_inventory = False

if "show_health_status" not in st.session_state:
    st.session_state.show_health_status = False

if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False

if "show_unmount_form" not in st.session_state:
    st.session_state.show_unmount_form = False

st.title("🧪Filament Management")

tab1, tab2 , tab3 = st.tabs(["Inventory", "Add Filament", "Mount Filament"])

#Allows user to logout
show_user_sidebar()

# --- Login check ---
require_login()
user_level = require_access("Filament Inventory", minimum_level="Read")

with tab1:
    # --- Show Inventory Buttons --- 
    toggle_button("show_active_inventory", "Show Active Filaments", "Hide Active Filaments")
    if st.session_state.get("show_active_inventory", False):
        try: 
            active = get_active_filaments()
            st.dataframe(active, use_container_width=True)
        except Exception as e:
            st.error("Could not load active filaments.")
            st.exception(e)
    
    st.divider()

    toggle_button("show_in_use_inventory", "Show In-Use Filaments", "Hide In-Use Filaments")
    if st.session_state.get("show_in_use_inventory", False):
        try:
            in_use = get_in_use_filaments()
            st.dataframe(in_use, use_container_width=True)
        except Exception as e:
            st.error("Could not load in-use filaments.")
            st.exception(e)
    
    st.divider()

    toggle_button("show_archived_inventory", "Show Archived Filaments", "Hide Archived Filaments")
    if st.session_state.get("show_archived_inventory", False):
        try:
            archived = get_archived_filaments()
            st.dataframe(archived, use_container_width=True)
        except Exception as e:
            st.error("Could not load archived filaments.")
            st.exception(e)



    # Show individual status
    st.divider()
    toggle_button("show_health_status", "Show Filament Health Status", "Hide Filament Health Status")

    if st.session_state.get("show_health_status", False):
        st.markdown("### Filament Health Status")

        try: 
            in_use = get_in_use_filaments()

            if not in_use:
                st.info("No filaments currently in use.")
            else:
                for filament in in_use:
                    remaining = filament.get("remaining_weight")
                    label = f"**{filament['serial_number']}** on {filament['printer_name']}"

                    if remaining is not None:
                        if remaining < 500:
                            st.error(f"{label} - **Critical** - Replace Now ({remaining}g left)")
                        elif remaining < 2500:
                            st.warning(f"{label} - **Low** - Prepare Replacement ({remaining}g left)")
                        else:
                            st.success(f"{label} - **OK** - ({remaining}g left)")
                    else:
                        st.info(f"{label} - Spool not currently mounted")
        except Exception as e:
            st.error("Failed to load filament health status.")
            st.exception(e)

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
        toggle_button("show_unmount_form", "Unmount Filament", "Hide Unmount Form")
    
    if st.session_state.get("show_mount_form", False) and user_level in ("Write", "Admin"):
        render_mount_form()

    if st.session_state.get("show_unmount_form", False) and user_level in ("Write", "Admin"):
        render_unmount_form()

    st.divider()
    toggle_button("show_acclimatize_form", "Move to Acclimatization", "Hide Acclimatization Form")

    if st.session_state.get("show_acclimatize_form", False) and user_level in ("Write", "Admin"):
        print("")
