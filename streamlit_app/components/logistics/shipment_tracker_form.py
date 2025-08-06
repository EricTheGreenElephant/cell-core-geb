import streamlit as st
import pandas as pd
import time
from services.shipment_services import (
    get_active_shipments,
    get_products_in_shipments,
    mark_shipment_as_shipped,
    mark_shipment_as_delivered
)
from db.orm_session import get_session


def render_shipment_tracker():
    """
    Creates form that allows user to update shipment status to shipped or delivered

    - Fetches outstanding shipments
    - Displays products in shipment in dataframe (table)
    - On submission, updates shipments table status to 'shipped' or 'delivered'
    - If shipped, updates product_tracking, product_status_history table products to shipped.
    """
    st.subheader("Shipment Tracker")

    with get_session() as db:
        shipments = get_active_shipments(db)

    if not shipments:
        st.info("No active shipments to display.")
        return

    for shipment in shipments:
        with st.expander(f"Shipment #{shipment['shipment_id']} to {shipment['customer_name']} ({shipment['status']})"):
            st.markdown(f"**Created:** {shipment['created_date'].strftime('%Y-%m-%d')} \n**Order ID:** {shipment['order_id']}")

            with get_session() as db:
                products = get_products_in_shipments(db, shipment["shipment_id"])
            df = pd.DataFrame(products)
            st.dataframe(df, hide_index=True, use_container_width=True)

            if shipment["status"] == "Pending":
                if st.button("Mark as Shipped", key=f"ship_{shipment['shipment_id']}"):
                    user_id = st.session_state.get("user_id")
                    with get_session() as db:
                        mark_shipment_as_shipped(db, shipment["shipment_id"], user_id)
                    st.success("Shipment marked as Shipped.")
                    time.sleep(1.5)
                    st.rerun()
            elif shipment["status"] == "Shipped":
                if st.button("Mark as Delivered", key=f"deliver_{shipment['shipment_id']}"):
                    with get_session() as db:
                        mark_shipment_as_delivered(db, shipment["shipment_id"])
                    st.success("Shipment marked as Delivered.")
                    time.sleep(1.5)
                    st.rerun()