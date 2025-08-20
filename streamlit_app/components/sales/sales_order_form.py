import streamlit as st
import time
from collections import defaultdict
from services.sales_services import (
    get_customers, 
    get_active_sales_catalogue, 
    get_orderable_product_types, 
    create_sales_order, 
    get_active_supplements,
    get_processing_order_with_items,
    update_sales_order,
    build_catalogue_quantity_inputs,
    show_order_quantity_summary,
    calculate_order_totals_from_catalogue
)
from services.shipment_services import cancel_order_request
from schemas.sales_schemas import SalesOrderInput
from db.orm_session import get_session
from utils.state_manager import StateManager


def render_sales_order_form(mode: str = "new"):
    st.subheader("Create Sales Order" if mode == "new" else "Update Sales Order")
    
    with get_session() as db:
        customers = get_customers(db)
        catalogues = get_active_sales_catalogue(db)
        product_types = get_orderable_product_types(db)
        supplements = get_active_supplements(db)

    if not all([customers, catalogues, product_types, supplements]):
        st.warning("Missing required setup data.")
        return
    
    product_lookup = {p.id: p.name for p in product_types}
    supplement_lookup = {s.id: s.name for s in supplements}

    # === Handle Order Selection if Updating ===
    order_data = None
    if mode == "update":
        with get_session() as db:
            orders = get_processing_order_with_items(db, all_orders=True)
        if not orders:
            st.warning("No active sales orders found.")
            return

        order_lookup = {
            f"Order #{o['order_id']} - {o['customer_name']} ({o['order_date'].date()})": o["order_id"]
            for o in orders
        }
        selected_label = st.selectbox("Select Sales Order to Edit", ["Select..."] + list(order_lookup.keys()))
        if selected_label == "Select...":
            return
        
        selected_order_id = order_lookup[selected_label]

        with get_session() as db:
            order_data = get_processing_order_with_items(db, selected_order_id)

        customer_id = order_data["customer_id"]
        notes = order_data["notes"] or ""

    else:
        customer_id = None
        notes = ""
    
    # === Customer Selection ===
    customer_options = {c["customer_name"]: c["id"] for c in customers}
    default_customer_idx = list(customer_options.values()).index(customer_id) if customer_id else 0
    customer_choice = st.selectbox("Select Customer", list(customer_options.keys()), index=default_customer_idx)

    # === Catalogue Quantities ===
    package_quantities = build_catalogue_quantity_inputs(catalogues, mode)
    
    # === Calculate Final Quantities ===
    product_quantities_raw, supplement_quantities_raw = calculate_order_totals_from_catalogue(
        catalogues=catalogues,
        package_quantities=package_quantities
    )
    product_quantities = defaultdict(int, product_quantities_raw)
    supplement_quantities = defaultdict(int, supplement_quantities_raw)

    # === Overlay Existing Order Quantities if Update Mode ===
    if mode == "update" and order_data:
        for item in order_data["product_items"]:
            product_quantities[item["product_type_id"]] += item["quantity"]
        for supp in order_data["supplements"]:
            supplement_quantities[supp["supplement_id"]] += supp["quantity"]

    # === Show Summary ===
    if any(package_quantities.values()) or mode == "update":
        show_order_quantity_summary(product_quantities, supplement_quantities, product_lookup, supplement_lookup)
    
    notes = st.text_area("Order Notes (Optional)", max_chars=255, value=notes).strip()

    # === Submission Buttons ===
    col1, col2 = st.columns(2)
    user_id = st.session_state.get("user_id")

    if col1.button("Update Sales Order" if mode == "update" else "Create Sales Order", use_container_width=True):
        data = SalesOrderInput(
            customer_id=customer_options[customer_choice],
            created_by=user_id,
            updated_by=user_id,
            product_quantities=dict(product_quantities),
            supplement_quantities=dict(supplement_quantities),
            notes=notes
        )

        try:
            with get_session() as db:
                if mode == "update":
                    update_sales_order(db=db, order_id=selected_order_id, data=data)
                else:
                    create_sales_order(db, data)
            st.success("Sales order created successfully.")
            time.sleep(1.5)
            StateManager.clear(scope="catalogue", id_=mode)
            st.rerun()
        except Exception as e:
            st.error("Failed to process sales order.")
            st.exception(e)
    # === Cancel Option ===
    if mode == "update":
        if col2.button("Cancel Sales Order", use_container_width=True):
            if not notes:
                st.warning("Cancellation requires a note.")
                return
            try:
                with get_session() as db:
                    cancel_order_request(
                        db=db,
                        order_id=selected_order_id,
                        user_id=user_id,
                        old_status=order_data["status"],
                        old_updated_by=order_data["updated_by"],
                        old_updated_at=str(order_data["updated_at"]),
                        notes=notes
                    )
                st.warning("Order cancelled.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to cancel sales order.")
                st.exception(e)