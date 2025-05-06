import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from data.filament import get_active_filaments, get_archived_filaments, get_in_use_filaments, get_all_filament_statuses
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.filament_form import render_add_filament_form
from components.filament_mount_form import render_mount_form
from components.filament_unmount_form import render_unmount_form
from components.filament_acclimatize_form import render_acclimatizing_form
from components.toggle import toggle_button


if "selected_statuses" not in st.session_state:
    st.session_state.selected_statuses = []

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

if "show_acclimatize_form" not in st.session_state:
    st.session_state.show_acclimatize_form = False

st.title("🧪Filament Management")

tab1, tab2 , tab3 = st.tabs(["Inventory", "Add Filament", "Mount Filament"])

#Allows user to logout
show_user_sidebar()

# --- Login check ---
require_login()
user_level = require_access("Filament Inventory", minimum_level="Read")

with tab1:
    # Show individual status
    toggle_button("show_health_status", "Show Filament Health Status", "Hide Filament Health Status")

    if st.session_state.get("show_health_status", False):
        st.markdown("### Filament Health Status")

        try:
            all_filaments = get_all_filament_statuses()
            in_use = [f for f in all_filaments if f["current_status"] == "In Use"]

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
    st.divider()

    # --- Active Filament Inventory with Filter ---
    toggle_button("show_active_inventory", "Show Active Filaments", "Hide Active Filaments")
    
    if st.session_state.get("show_active_inventory", False):
        try:
            all_filaments = get_all_filament_statuses()

            if all_filaments:
                df_filaments = pd.DataFrame(all_filaments)

                gb = GridOptionsBuilder.from_dataframe(df_filaments)
                gb.configure_pagination(paginationAutoPageSize=True)
                gb.configure_side_bar()
                # Explicitly enforce filtering for "current_status"
                gb.configure_column("current_status", filter="agSetColumnFilter")
                gb.configure_default_column(filterable=True, sortable=True, resizable=True)
                gridOptions = gb.build()

                AgGrid(
                    df_filaments,
                    gridOptions=gridOptions,
                    enable_enterprise_modules=True,
                    height=500,
                    fit_columns_on_grid_load=False,
                    reload_data=True,
                )
            else:
                st.warning("No active filaments available.")
        except Exception as e:
            st.error("Could not load active filaments.")
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