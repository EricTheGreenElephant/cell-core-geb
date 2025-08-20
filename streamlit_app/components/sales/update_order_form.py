import streamlit as st
import time
from collections import defaultdict
from db.orm_session import get_session
from services.shipment_services import cancel_order_request, get_open_order_headers
from services.sales_services import (
    get_customers,
    get_active_sales_catalogue,
    get_orderable_product_types,
    get_active_supplements,
    get_processing_order_with_items, 
    update_sales_order,
    # get_product_type_names,
    # get_supplement_names
)
from schemas.sales_schemas import SalesOrderInput

def render_update_order_form():
    st.subheader("Update or Cancel Existing Sales Orders")

    with get_session() as db:
        orders = get_processing_order_with_items(db=db, all_orders=True)

    if not orders:
        st.info("No orders found with 'Processing' status.")
        return
    
    order_lookup = {
        f"Order #{o['order_id']} - {o['customer_name']} ({o['order_date'].date()})": o
        for o in orders
    }

    selected_label = st.selectbox("Select Order to Edit", ["Select..."] + list(order_lookup.keys()))
    if selected_label == "Select...":
        return
    
    selected_order = order_lookup[selected_label]
    selected_order_id = selected_order["order_id"]

    with get_session() as db:
        customers = get_customers(db)
        catalogues = get_active_sales_catalogue(db)
        product_types = get_orderable_product_types(db)
        supplements = get_active_supplements(db)

    customer_options = {c["customer_name"]: c["id"] for c in customers}
    customer_choice = [
        k for k, v in customer_options.items() if v == selected_order["customer_id"]
    ][0]
    customer_selected = st.selectbox(
        "Select Customer", 
        list(customer_options.keys()),
        index=list(customer_options.keys()).index(customer_choice)
    )

    product_lookup = {p.id: p.name for p in product_types}
    supplement_lookup = {s.id: s.name for s in supplements}

    st.markdown("#### Select Catalogue Packages and Quantities")

    existing_product_counts = defaultdict(int)
    for item in selected_order["product_items"]:
        existing_product_counts[item["product_type_id"]] += item["quantity"]

    existing_supplement_counts = defaultdict(int)
    for item in selected_order["supplements"]:
        existing_supplement_counts[item["supplement_id"]] += item["quantity"]

    package_quantities = {}
    for cat in catalogues:
        est_count = 0
        for p in cat.products:
            prod_id = p.product_id
            if prod_id in existing_product_counts and p.product_quantity > 0:
                count = existing_product_counts[prod_id] // p.product_quantity
                est_count = max(est_count, count)
        
        with st.expander(f"{cat.package_name} (${cat.price:.2f})"):
            st.markdown(f"*{cat.package_desc}*")
            qty = st.number_input(
                label="Quantity",
                min_value=0,
                step=1,
                value=est_count,
                key=f"catalogue_{cat.id}"
            )
            package_quantities[cat.id] = qty
    
    product_quantities = defaultdict(int)
    supplement_quantities = defaultdict(int)

    for cat in catalogues:
        count = package_quantities.get(cat.id, 0)
        if count == 0:
            continue
        for p in cat.products:
            product_quantities[p.product_id] += p.product_quantity * count
        for s in cat.supplements:
            supplement_quantities[s.supplement_id] += s.supplement_quantity * count

    if any(package_quantities.values()):
        st.markdown("#### Summary of Updated Order Quantities")
        st.markdown("**Products:**")
        for pid, qty in product_quantities.items():
            name = product_lookup.get(pid, f"Unknown Product ({pid})")
            st.markdown(f"- {name}: {qty}")

        if supplement_quantities:
            st.markdown("**Supplements:**")
            for sid, qty in supplement_quantities.items():
                name = supplement_lookup.get(sid, f"Unknown Supplement ({sid})")
                st.markdown(f"- {name}: {qty}")
    
    notes = st.text_area("Order Notes (Optional)", value=selected_order["notes"] or "", max_chars=255).strip()
    user_id = st.session_state.get("user_id")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Update Sales Order", use_container_width=True):
            try:
                data = SalesOrderInput(
                    customer_id=customer_options[customer_selected],
                    created_by=user_id,
                    updated_by=user_id,
                    product_quantities=dict(product_quantities),
                    supplement_quantities=dict(supplement_quantities),
                    notes=notes
                )
                with get_session() as db:
                    update_sales_order(db, selected_order_id, data)
                st.success("Sales order updated successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to update sales order.")
                st.exception(e)
    
    with col2:
        if st.button("Cancel Order", use_container_width=True):
            if not notes:
                st.warning("Cancellation requires a notes.")
                return
            try:
                with get_session() as db:
                    cancel_order_request(
                        db=db,
                        order_id=selected_order_id,
                        user_id=user_id,
                        old_status=selected_order['status'],
                        old_updated_by=selected_order['updated_by'],
                        old_updated_at=str(selected_order['updated_at']),
                        notes=notes
                    )
                st.warning("Order cancelled.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to cancel order.")
                st.exception(e)


    # with get_session() as db:
    #     open_orders = get_open_order_headers(db)

    # if not open_orders:
    #     st.info("No active orders with status 'Processing'.")
    #     return
    
    # order_lookup = {
    #     f"Order #{o['order_id']} - {o['customer_name']} ({o['order_date'].date()})": o
    #     for o in open_orders
    # }
    
    # selected_label = st.selectbox("Select Order to Edit or Cancel", ["Select..."] + list(order_lookup.keys()))
    # if selected_label == "Select...":
    #     return
    
    # selected_order = order_lookup[selected_label]
    # selected_order_id = selected_order["order_id"]

    # with get_session() as db:
    #     order_data = get_processing_order_with_items(db, selected_order_id)

    # if not order_data:
    #     st.warning("Order not found or not in 'Processing' status.")
    #     return

    # # st.markdown(f"**Customer:** {selected_order['customer']}")
    # # st.markdown(f"**Order Date:** {selected_order['order_date'].strftime('%Y-%d-%m')}")
    # # st.markdown("---")

    # with get_session() as db:
    #     product_names = get_product_type_names(db)
    #     supplement_names = get_supplement_names(db)

    # st.markdown("### Update Product Quantities")
    # updated_products = {}
    # for item in order_data["product_items"]:
    #     current_qty = item["quantity"]
    #     label = f"{product_names.get(item['product_type_id'], 'Unknown Product')} (was {current_qty})"
    #     new_qty = st.number_input(label, min_value=0, step=1, value=current_qty, key=f"prod_{item['id']}")
    #     updated_products[item["id"]] = new_qty

    # # product_quantities = defaultdict(int)
    # # for item in selected_order['items']:
    # #     new_qty = st.number_input(
    # #         f"{item['product_type']}",
    # #         min_value=0,
    # #         step=1,
    # #         value=item['quantity'],
    # #         key=f"prod_{item['product_type']}"
    # #     )
    # #     product_quantities[item['product_type_id']] = new_qty

    # st.markdown("### Update Supplement Quantities")
    # updated_supplements = {}
    # for supp in order_data["supplements"]:
    #     current_qty = supp["quantity"]
    #     label = f"{supplement_names.get(supp['supplement_id'], 'Unknown Supplement')} (was {current_qty})"
    #     new_qty = st.number_input(label, min_value=0, step=1, value=current_qty, key=f"supp_{supp['id']}")
    #     updated_supplements[supp["id"]] = new_qty

    # # supplement_quantities = defaultdict(int)
    # # for item in selected_order.get('supplements', []):
    # #     new_qty = st.number_input(
    # #         f"{item['name']}",
    # #         min_value=0,
    # #         step=1,
    # #         value=item['quantity'],
    # #         key=f"supp_{item['name']}"
    # #     )
    # #     supplement_quantities[item['supplement_id']] = new_qty

    # notes = st.text_area("Update Notes (Optional)", value=order_data["notes"] or "", max_chars=255).strip()

    # col1, col2 = st.columns(2)
    # user_id = st.session_state.get("user_id")

    # with col1:
    #     if st.button("Update Order", use_container_width=True):
    #         try: 
    #             data = SalesOrderInput(
    #                 customer_id=selected_order["customer_id"],
    #                 created_by=user_id,
    #                 updated_by=user_id,
    #                 notes=notes,
    #                 product_quantities={
    #                     item["product_type_id"]: qty
    #                     for item_id, qty in updated_products.items()
    #                     for item in order_data["product_items"]
    #                     if item["id"] == item_id
    #                 },
    #                 supplement_quantities={
    #                     supp["supplement_id"]: new_qty
    #                     for supp_id, qty in updated_supplements.items()
    #                     for supp in order_data["supplements"]
    #                     if supp["id"] == supp_id
    #                 }
    #             )
    #             with get_session() as db:
    #                 update_sales_order(
    #                     db=db,
    #                     order_id=selected_order_id,
    #                     data=data
    #                 )
    #             st.success("Order updated successfully.")
    #             time.sleep(1.5)
    #             st.rerun()
    #         except Exception as e:
    #             st.error("Failed to update order.")
    #             st.exception(e)
    
    # with col2: 
    #     if st.button("Cancel Order", use_container_width=True):
    #         if not notes:
    #             st.warning("Cancellation requires a note explaining the reason.")
    #             return
    #         try:
    #             with get_session() as db:
    #                 cancel_order_request(
    #                     db=db,
    #                     order_id=selected_order_id,
    #                     user_id=user_id,
    #                     old_status=selected_order['status'],
    #                     old_updated_by=selected_order['updated_by'],
    #                     old_updated_at=str(selected_order['updated_at']),
    #                     notes=notes
    #                 )
    #             st.warning("Order cancelled.")
    #             time.sleep(1.5)
    #             st.rerun()
    #         except Exception as e:
    #             st.error("Failed to cancel order.")
    #             st.exception(e)