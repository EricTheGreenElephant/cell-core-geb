import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from services.filament_service import get_all_filament_statuses
from db.orm_session import get_session

def render_filament_inventory():
    """
    Provides a table of view of all filament spools. 

    - Fetches all filaments with database query
    - Builds dataframe (table) 
    """
    try:
        # Creates database session and calls services function to query all filament data
        with get_session() as db:
            all_filaments = get_all_filament_statuses(db)

        if all_filaments:

            # Builds dataframe with returned data and creates display
            df_filaments = pd.DataFrame(all_filaments)
            
            df_filaments["initial_weight"] = pd.to_numeric(df_filaments["initial_weight"], errors="coerce")
            df_filaments["remaining_weight"] = pd.to_numeric(df_filaments["remaining_weight"], errors="coerce")

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