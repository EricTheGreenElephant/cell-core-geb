import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from data.filament import get_all_filament_statuses

def render_filament_inventory():
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