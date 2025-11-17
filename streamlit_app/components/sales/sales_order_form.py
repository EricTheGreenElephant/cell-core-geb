import streamlit as st
import time
from services.sales_services import (
    get_customers, 
    get_active_skus,
    get_sales_ready_qty_by_sku,
    create_sales_order, 
    get_processing_order_with_items,
    update_sales_order,
    # show_order_quantity_summary,
    # calculate_order_totals_from_catalogue
)
from services.shipment_services import cancel_order_request
from schemas.sales_schemas import SalesOrderInput
from db.orm_session import get_session
from utils.state_manager import StateManager


def render_sales_order_form(mode: str = "new"):
    st.subheader("Create Sales Order" if mode == "new" else "Update Sales Order")
    
    with get_session() as db:
        customers = get_customers(db)
        skus = get_active_skus(db)
        available_by_sku = get_sales_ready_qty_by_sku(db)

    if not customers or not skus:
        st.warning("Missing customers or SKUs.")
        return
    
    customer_options = {c["customer_name"]: c["id"] for c in customers}

    # === Handle Order Selection if Updating ===
    order_data = None
    selected_order_id = None
    if mode == "update":
        with get_session() as db:
            existing = get_processing_order_with_items(db, all_orders=True)
        if not existing:
            st.warning("No active sales orders found.")
            return

        order_lookup = {
            f"Order #{o['order_id']} - {o['customer_name']} ({o['order_date'].date()})": o
            for o in existing
        }
        selected_label = st.selectbox("Select Sales Order to Edit", ["Select..."] + list(order_lookup.keys()))
        if selected_label == "Select...":
            return
        
        order_data = order_lookup[selected_label]
        selected_order_id = order_data["order_id"]

    default_idx = 0
    if mode == "update":
        cur_id = order_data["customer_id"]
        if cur_id in customer_options.values():
            default_idx = list(customer_options.values()).index(cur_id)
    customer_label = st.selectbox("Customer", list(customer_options.keys()), index=default_idx)


    # SKU table of inputs
    st.markdown("#### Select SKU quantities")
    sku_quantities: dict[int, int] = {}
    existing_map = {}
    if mode == "update" and order_data:
        existing_map = {i["product_sku_id"]: i["quantity"] for i in order_data["order_items"]}

    for row in skus:
        sid = row["id"]
        sku_code = row["sku"]
        name = row["name"]
        is_bundle = bool(row["is_bundle"])

        avail = available_by_sku.get(sid)
        hint = f" (Available: {avail})" if avail is not None else ""
        default_val = existing_map.get(sid, 0)
        qty = st.number_input(
            f"{sku_code} - {name}{' **--BUNDLE**' if is_bundle else ''} {hint}",
            min_value=0, step=1, value=default_val, key=f"skuqty_{sid}"
        )
        if qty > 0:
            sku_quantities[sid] = qty
    
    notes_default = (order_data["notes"] or "") if (mode == "update" and order_data) else ""
    notes = st.text_area("Order Notes (optional)", value=notes_default, max_chars=255).strip()

    col1, col2 = st.columns(2)
    user_id = st.session_state.get("user_id")

    if col1.button("Update Order" if mode == "update" else "Create Order", width='stretch'):
        data = SalesOrderInput(
            customer_id=customer_options[customer_label],
            created_by=user_id,
            updated_by=user_id,
            sku_quantities=sku_quantities,
            notes=notes,
            parent_order_id=(order_data["parent_order_id"] if mode == "update" else None)
        )
        try:
            with get_session() as db:
                if mode == "update":
                    update_sales_order(db, selected_order_id, data)
                else:
                    create_sales_order(db, data)
            st.success("Order processed.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to process order.")
            st.exception(e)

    # === Cancel Option ===
    if mode == "update":
        if col2.button("Cancel Sales Order", width='stretch'):
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