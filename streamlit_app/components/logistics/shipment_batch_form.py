import streamlit as st
import pandas as pd
import time
from services.shipment_services import (
    get_open_order_headers,
    get_open_orders_with_items, 
    get_fifo_inventory_by_type, 
    create_shipment_from_order,
    cancel_order_request
)
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

    # === Fetch Open Orders ===
    with get_session() as db:
        order_headers = get_open_order_headers(db)

    if not order_headers:
        st.info("No open sales orders available for fulfillment.")
        return
    
    order_lookup = {
        f"Order #{o['order_id']} - {o['customer_name']} ({o['order_date'].date()})": o
        for o in order_headers
    }
    selected_label = st.selectbox("Select Sales Order", ["Select..."] + list(order_lookup.keys()))
    if selected_label == "Select...":
        return
    
    selected_order = order_lookup[selected_label]
    selected_order_id = selected_order["order_id"]

    with get_session() as db:
        details = get_open_orders_with_items(db, selected_order_id)
    
    if not details:
        st.error("No open sales orders available for fulfillment.")
        return

    # === Display Header ===
    st.markdown(f"**Customer:** {selected_order['customer_name']}")
    st.markdown(f"**Order Date:** {selected_order['order_date'].strftime('%Y-%d-%m')}")
    if selected_order["notes"]:
        st.markdown(f"**Notes:** {selected_order['notes']}")
    if selected_order["parent_order_id"]:
        st.markdown(f"**Parent Order:** {selected_order['parent_order_id']}")
    st.markdown("---")

    # === Display Supplements Requested ===
    supplements = details.get("supplements", [])
    if supplements:
        st.markdown("**Requested Supplement Items:**")
        for s in supplements:
            st.markdown(f"- {s['supplement_name']}: {s['quantity']}")
        st.markdown("---")
    
    # === Inventory Fulfillment Logic ===
    all_selected_products = {}
    invalid_fulfillments = []

    for item in details["items"]:
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

    notes = st.text_area(label="Notes (Required if canceling order):", max_chars=255)

    # === Action Buttons ===
    user_id = st.session_state.get("user_id")
    col1, col2 = st.columns([1, 1])

    with col1:
        canceled = st.button("Cancel Order Request", type="secondary", use_container_width=True)
    with col2:
        submitted = st.button("Create Shipment", type="primary", use_container_width=True)
    
    # === Cancel Logic ===
    if canceled:
        if not notes:
            st.warning("Notes required for a canceled order request!")
            return
        try:
            with get_session() as db:
                cancel_order_request(
                    db=db, 
                    order_id=selected_order_id, 
                    user_id=user_id, 
                    notes=notes,
                    old_status=selected_order["status"],
                    old_updated_by=selected_order["updated_by"],
                    old_updated_at=str(selected_order["updated_at"])
                )
            st.warning("Order canceled.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to cancel request.")
            st.exception(e)

    # === Submission Logic ===
    if submitted:
        if invalid_fulfillments:
            st.error(f"Shipment cannot be created. These product types are incomplete: {', '.join(invalid_fulfillments)}")
            return

        try:
            with get_session() as db:
                create_shipment_from_order(
                    db=db,
                    order_id=selected_order_id,
                    customer_id=selected_order["customer_id"],
                    creator_id=user_id,
                    updated_by=user_id,
                    selected_products_by_type=all_selected_products,
                    notes=notes
                )
            st.success("Shipment created successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to create shipment.")
            st.exception(e)