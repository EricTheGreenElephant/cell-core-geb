import streamlit as st
from data.product_status import get_all_product_status


def render_status_tracker():
    st.subheader("Product Status Tracker")

    try:
        status_data = get_all_product_status()
        st.dataframe(status_data, use_container_width=True)
    except Exception as e:
        st.error("Could not load product status.")
        st.exception(e)