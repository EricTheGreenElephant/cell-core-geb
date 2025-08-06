import streamlit as st
from services.lid_services import get_lid_inventory
from services.seal_services import get_seal_inventory
from db.orm_session import get_session


def render_lids_seals_inventory(mode):
    """
    Creates inventory dataframe (table) view

    Parameters
        mode: str
            Passed parameter from component of either 'Lid' or 'Seal'

    - Fetches available lids or seals based on selection (mode) passed
    """
    st.subheader(f"{mode} Inventory")

    try:
        with get_session() as db:
            if mode == "Lid":
                inventory = get_lid_inventory(db)
            elif mode == "Seal":
                inventory = get_seal_inventory(db)
        
        if inventory:
            st.dataframe(inventory, use_container_width=True)
        else:
            st.info("No inventory available.")

    except Exception as e:
        st.error("Failed to load inventory.")
        st.exception(e)

