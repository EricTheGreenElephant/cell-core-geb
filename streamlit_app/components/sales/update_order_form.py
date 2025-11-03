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
        if st.button("Update Sales Order", width='stretch'):
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
        if st.button("Cancel Order", width='stretch'):
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
