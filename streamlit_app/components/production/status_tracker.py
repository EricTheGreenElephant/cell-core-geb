import streamlit as st
from services.product_status_services import get_all_product_status
from components.common.refresh_tools import refresh_cache
from db.orm_session import get_session


@st.cache_data
def load_product_status_data():
    with get_session() as db:
        return get_all_product_status(db)
    
def render_status_tracker():
    st.subheader("Product Status Tracker")

    if refresh_cache("Refresh Product List", key="refresh_status"):
        load_product_status_data.clear()

    try:
        # with get_session() as db:
            # status_data = get_all_product_status(db)
        status_data = load_product_status_data()
        st.dataframe(status_data, width='stretch')
    except Exception as e:
        st.error("Could not load product status.")
        st.exception(e)