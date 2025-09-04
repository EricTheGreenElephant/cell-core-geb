import streamlit as st
import pandas as pd
import time
from services.shipment_services import (
    get_open_order_headers,
    get_open_orders_with_items, 
    expand_order_skus_to_components,
    get_fifo_inventory_by_sku, 
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
        component_need = expand_order_skus_to_components(db, details["items"])
    
    if not component_need:
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

    # === Display lines as ordered ===
    picked_by_component: dict[int, list[dict]] = {}
    non_serialized_counts: dict[int, int] = {}
    invalid_components: list[str] = []

    for comp_sku_id, comp in component_need.items():
        required = int(comp["required_qty"])
        sku_label = f"{comp['sku']} - {comp['sku_name']}"
        st.markdown(f"#### {sku_label} (need {required})")

        if not comp["is_serialized"]:
            st.info("Non-serialized item - no unit picking required.")
            st.markdown(f"*Quantity to ship:* **{required}**")
            non_serialized_counts[comp_sku_id] = required
            picked_by_component[comp_sku_id] = []
            st.markdown("---")
            continue

        with get_session() as db:
            fifo = get_fifo_inventory_by_sku(db, comp_sku_id, required)

        if fifo and len(fifo) > 0:
            st.markdown("*Auto-selected by FIFO*")
            st.data_editor(pd.DataFrame(fifo), hide_index=True, num_rows="fixed", disabled=True, key=f"fifo_{comp_sku_id}")
        else:
            st.warning(f"No available inventory found for {comp['sku']}.")

        override = st.checkbox(f"Manual override for {comp['sku']}", key=f"ovr_{comp_sku_id}")

        if override:
            with get_session() as db:
                all_inv = get_fifo_inventory_by_sku(db, comp_sku_id, 500)

            options = [f"#{u['product_id']} | {u['print_date'].strftime('%Y-%d-%m')}" for u in all_inv]
            lookup = {lbl: u for lbl, u in zip(options, all_inv)}
            default = options[:required] if options else []

            chosen = st.multiselect(f"Pick {required} unit(s) for {comp['sku']}", options=options, default=default, key=f"ms_{comp_sku_id}")
            chosen_units = [lookup[x] for x in chosen]
            if len(chosen_units) != required:
                invalid_components.append(comp["sku"])
            picked_by_component[comp_sku_id] = chosen_units
        else:
            picked_by_component[comp_sku_id] = fifo or []
            if len(picked_by_component[comp_sku_id]) != required:
                invalid_components.append(comp["sku"])
        
        st.markdown("---")

    notes = st.text_area("Notes (Required if canceling order):", max_chars=255).strip()

    user_id = st.session_state.get("user_id")
    col1, col2 = st.columns([1, 1])

    with col1:
        canceled = st.button("Cancel Order Request", type="secondary", use_container_width=True)
    with col2:
        submitted = st.button("Create Shipment", type="primary", use_container_width=True)

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

    if submitted:
        if invalid_components:
            st.error("Shipment cannot be created. Incomplete component picks: " + ", ".join(invalid_components))
            return
        try:
            with get_session() as db:
                create_shipment_from_order(
                    db=db,
                    order_id=selected_order_id,
                    customer_id=selected_order["customer_id"],
                    creator_id=user_id,
                    updated_by=user_id,
                    picked_by_component=picked_by_component,
                    non_serialized_counts=non_serialized_counts,
                    notes=notes
                )
            st.success("Shipment created successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to create shipment.")
            st.exception(e)
