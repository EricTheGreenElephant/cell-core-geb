import time
import streamlit as st
from db.orm_session import get_session
from services.sales_services import get_canceled_order_headers, get_canceled_orders_with_items, create_sales_order
from schemas.sales_schemas import SalesOrderInput


def render_canceled_orders_form():
    st.subheader("Re-Submit Canceled Orders")

    with get_session() as db:
        canceled_headers = get_canceled_order_headers(db)

    if not canceled_headers:
        st.info("No canceled orders found.")
        return
    
    order_lookup = {
        f"Order #{o['order_id']} - {o['customer_name']} ({o['order_date'].date()})": o
        for o in canceled_headers
    }
    selected_label = st.selectbox("Select a canceled order to re-submit", ["Select..."] + list(order_lookup.keys()))

    if selected_label == "Select...":
        return
    
    selected_order = order_lookup[selected_label]
    
    with get_session() as db:
        details = get_canceled_orders_with_items(db, selected_order["order_id"])
    
    if not details:
        st.error("Order details could not be found.")
    
    st.markdown(f"**Original Notes:** {selected_order['notes'] or 'N/A'}")

    st.markdown("#### Product Quantities")
    product_quantities = {}
    for item in details["product_items"]:
        qty = st.number_input(
                label=f"{item['product_type']}",
                min_value=0,
                value=item["quantity"],
                step=1,
                key=f"prod_{item['product_type_id']}"
        )
        if qty > 0:
            product_quantities[item["product_type_id"]] = qty

    st.markdown("#### Supplement Quantities")
    supplement_quantities = {}
    if details["supplements"]:
        for supp in details["supplements"]:
            qty = st.number_input(
                label=f"{supp['supplement_name']}",
                min_value=0,
                value=supp["quantity"],
                step=1,
                key=f"supp_{supp['supplement_id']}"
            )
            if qty > 0:
                supplement_quantities[supp["supplement_id"]] = qty
    else:
        st.info("No supplements in the original order.")
        
    updated_notes = st.text_area("Updated Notes (optional)", max_chars=255).strip()
    
    submitted = st.button("Submit New Order")

    if submitted:
        if not product_quantities:
            st.warning("At least one product quantity must be greater than zero.")
            return
        
        user_id = st.session_state.get("user_id")

        data =  SalesOrderInput(
                customer_id=selected_order['customer_id'],
                created_by=user_id,
                updated_by=user_id,
                product_quantities=product_quantities,
                supplement_quantities=supplement_quantities,
                notes=f"Recreated from canceled order #{selected_order['order_id']}. {updated_notes}",
                parent_order_id=selected_order["order_id"]
            )
        try:
            with get_session() as db:
                create_sales_order(db, data)
            st.success("New sales order created successfully.")
            st.rerun()
        except Exception as e:
            st.error("Failed to create new order.")
            st.exception(e)

