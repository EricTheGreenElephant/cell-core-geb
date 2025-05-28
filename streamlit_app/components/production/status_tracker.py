import streamlit as st
from services.product_status_services import get_all_product_status
from db.orm_session import get_session

def render_status_tracker():
    st.subheader("Product Status Tracker")

    try:
        with get_session() as db:
            status_data = get_all_product_status(db)
        st.dataframe(status_data, use_container_width=True)
    except Exception as e:
        st.error("Could not load product status.")
        st.exception(e)