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
    help_text = "Auf Deutsch: Daten Aktualisieren"
    if refresh_cache("Refresh Product List", help=help_text, key="refresh_status"):
        load_product_status_data.clear()

    try:
        status_data = load_product_status_data()
        st.dataframe(status_data, width='stretch', column_config={"pressure_drop": st.column_config.NumberColumn(format="%.3f")})
        
    except Exception as e:
        st.error("Could not load product status.")
        st.exception(e)