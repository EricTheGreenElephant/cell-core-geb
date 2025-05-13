import streamlit as st
from data.lids import get_lid_inventory


def render_lid_inventory():
    st.markdown("Lid Inventory")

    try:
        lids = get_lid_inventory()
        if lids:
            st.dataframe(lids, use_container_width=True)
        else:
            st.info("No lid inventory available.")
    except Exception as e:
        st.error("Failed to load lid inventory.")
        st.exception(e)

