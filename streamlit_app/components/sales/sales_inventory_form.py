import streamlit as st
from services.sales_services import get_sales_ready_inventory
from db.orm_session import get_session


def render_sales_tab():
    st.subheader("Sales-Ready Inventory")

    with get_session() as db:
        rows = get_sales_ready_inventory(db)

    if not rows:
        st.info("No products currently available for sale.")
    else:
        st.dataframe(rows, width='stretch')