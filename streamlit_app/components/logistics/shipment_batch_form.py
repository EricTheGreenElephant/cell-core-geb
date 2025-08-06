import streamlit as st
import pandas as pd
import time
from services.shipment_services import get_open_orders_with_items, get_fifo_inventory_by_type, create_shipment_from_order
from db.orm_session import get_session


def render_shipment_batch_form():
    """
    Creates form that allows user to create shipment batch based on order request. 

    - Fetches open order requests
    - Automatically fetches available inventory by First-in, First-out basis
    - Allows user to manually override inventory selection
    - Prevent user from submitted if not enough inventory available for order request
    - On submission
        - Updates product stage on product_tracking and product_status_history table
        - Inserts records to shipment and shipment_items table
        - Updates status on orders table
    """
    st.subheader("Create Shipment from Sales Order")

    with get_session() as db:
        orders = get_open_orders_with_items(db)

    if not orders:
        st.info("No open sales orders available for fulfillment.")
        return
    
    order_choices = {f"Order #{oid} - {data['customer']}": oid for oid, data in orders.items()}
    selected_label = st.selectbox("Select Sales Order", list(order_choices.keys()))
    selected_order_id = order_choices[selected_label]
    selected_order = orders[selected_order_id]

    st.markdown(f"**Customer:** {selected_order['customer']} \n**Order Date:** {selected_order['order_date']}")

    all_selected_products = {}
    invalid_fulfillments = []

    for item in selected_order["items"]:
        product_type = item["product_type"]
        quantity_needed = item["quantity"]

        st.markdown(f"#### {product_type} ({quantity_needed} requested)")

        with get_session() as db:
            fifo_inventory = get_fifo_inventory_by_type(db, product_type, quantity_needed)

        if not fifo_inventory:
            st.warning(f"No available inventory for {product_type}.")
            all_selected_products[product_type] = []
            invalid_fulfillments.append(product_type)
            continue

        override = st.checkbox(f"Manual override for {product_type}", key=f"override_{product_type}")

        if override:
            with get_session() as db:
                all_inventory = get_fifo_inventory_by_type(db, product_type, 100)

            option_labels = [
                f"#{p['product_id']} | {p['print_date'].strftime('%Y-%m-%d')}" for p in all_inventory
            ]
            product_lookup = {label: p for label, p in zip(option_labels, all_inventory)}

            selected_options = st.multiselect(
                f"Select products manually for {product_type}",
                options=option_labels,
                default=option_labels[:quantity_needed],
                key=f"manual_{product_type}"
            )

            selected_inventory = [product_lookup[label] for label in selected_options]
            if len(selected_inventory) != quantity_needed:
                invalid_fulfillments.append(product_type)

            df = pd.DataFrame(selected_inventory)
            st.data_editor(df, hide_index=True, num_rows='fixed', key=f"manual_table_{product_type}")
        else:
            selected_inventory = fifo_inventory
            if len(selected_inventory) != quantity_needed:
                invalid_fulfillments.append(product_type)

            st.markdown("*Auto-selected by FIFO*")
            df = pd.DataFrame(fifo_inventory)
            st.data_editor(df, hide_index=True, num_rows="fixed", disabled=True, key=f"fifo_{product_type}")

        all_selected_products[product_type] = selected_inventory

    submitted = st.button("Create Shipment", use_container_width=True)
    if submitted:
        if invalid_fulfillments:
            st.error(f"Shipment cannot be created. These product types are incomplete: {', '.join(invalid_fulfillments)}")
            return

        try:
            user_id = st.session_state.get("user_id")
            with get_session() as db:
                create_shipment_from_order(
                    db=db,
                    order_id=selected_order_id,
                    customer_id=selected_order["customer_id"],
                    creator_id=user_id,
                    selected_products_by_type=all_selected_products
                )
            st.success("Shipment created successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to create shipment.")
            st.exception(e)