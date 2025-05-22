import streamlit as st
from services.lid_services import get_lid_inventory
from db.orm_session import get_session


def render_lid_inventory():
    st.markdown("Lid Inventory")

    try:
        with get_session() as db:
            lids = get_lid_inventory(db)
            
        if lids:
            st.dataframe(lids, use_container_width=True)
        else:
            st.info("No lid inventory available.")
    except Exception as e:
        st.error("Failed to load lid inventory.")
        st.exception(e)

