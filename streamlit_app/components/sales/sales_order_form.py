import streamlit as st
import time
from services.sales_services import get_customers, get_orderable_product_types, create_sales_order
from schemas.sales_schemas import SalesOrderInput
from db.orm_session import get_session


def render_sales_order_form():
    st.subheader("Create Sales Order")

    with get_session() as db:
        customers = get_customers(db)
        inventory = get_orderable_product_types(db)

    if not customers:
        st.warning("No customers found in the system.")
        st.stop()
    
    if not inventory:
        st.warning("No sales-ready products available.")
        st.stop()
    
    customer_options = {c['customer_name']: c['id'] for c in customers}
    customer_choice = st.selectbox("Select Customer", list(customer_options.keys()))

    st.markdown("#### Select Quantities for Each Product Type")

    mini_qty_validation = "CS MINI"
    invalid_input = False

    select_quantities = {}
    for product_type in inventory:
        qty = st.number_input(
            label=f"{product_type.name}",
            min_value=0,
            step=1,
            key=f"qty_{product_type.name}"
        )
        select_quantities[product_type.name] = qty

        if product_type.name == mini_qty_validation and qty % 3 != 0 and qty != 0:
            st.warning(f"{product_type.name} must be sold in multiples of 3.")
            invalid_input = True

    submitted = st.button("Create Sales Order", use_container_width=True)
    if submitted:
        if invalid_input:
            st.error("Please correct the invalid quantities before submitting.")
            st.stop()
            
        user_id = st.session_state.get("user_id")

        data = SalesOrderInput(
            customer_id=customer_options[customer_choice],
            created_by=user_id,
            product_quantities=select_quantities
        )

        try:
            with get_session() as db:
                create_sales_order(db, data)
            st.success("Sales order created successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to create order.")
            st.exception(e)