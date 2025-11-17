import streamlit as st
import pandas as pd
import time
from services.shipment_services import (
    get_active_shipments,
    get_products_in_shipments,
    get_open_orders_with_items,
    get_non_serialized_in_shipment,
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
                order_request = get_open_orders_with_items(db, shipment["order_id"])
                products = get_products_in_shipments(db, shipment["shipment_id"])
                supplements = get_non_serialized_in_shipment(db, shipment["shipment_id"])

            st.markdown("#### Order Request")
            order_df = pd.DataFrame(order_request["items"])
            st.dataframe(order_df, hide_index=True, width='stretch')

            st.divider()

            st.markdown("#### Chosen Products")
            df = pd.DataFrame(products)
            st.dataframe(df, hide_index=True, width='stretch')

            df2 = pd.DataFrame(supplements)
            st.dataframe(df2, hide_index=True, width='stretch')

            if shipment["status"] == "Pending":
                carrier = st.text_input("Carrier", key=f"carrier_{shipment['shipment_id']}").strip()
                tracking_number = st.text_input("Tracking Number", key=f"tracking_{shipment['shipment_id']}").strip()

                if st.button("Mark as Shipped", key=f"ship_{shipment['shipment_id']}"):
                    if not carrier or not tracking_number:
                        st.warning("Carrier and Tracking Number are required to ship.")
                        return
                    
                    user_id = st.session_state.get("user_id")
                    with get_session() as db:
                        mark_shipment_as_shipped(
                            db=db, 
                            shipment_id=shipment["shipment_id"], 
                            user_id=user_id,
                            carrier=carrier,
                            tracking_number=tracking_number
                        )
                    st.success("Shipment marked as Shipped.")
                    time.sleep(1.5)
                    st.rerun()
            elif shipment["status"] == "Shipped":
                st.markdown(f"**Carrier:** {shipment.get('carrier') or 'N/A'}")
                st.markdown(f"**Tracking #:** {shipment.get('tracking_number') or 'N/A'}")
                
                if st.button("Mark as Delivered", key=f"deliver_{shipment['shipment_id']}"):
                    with get_session() as db:
                        mark_shipment_as_delivered(db, shipment["shipment_id"])
                    st.success("Shipment marked as Delivered.")
                    time.sleep(1.5)
                    st.rerun()