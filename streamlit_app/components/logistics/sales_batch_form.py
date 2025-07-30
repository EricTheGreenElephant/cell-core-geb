import streamlit as st
from services.sales_services import get_customers, get_sales_ready_quantities_by_type
from db.orm_session import get_session


def render_sales_batch_form():
    st.subheader("Create Sales Batch")

    with get_session() as db:
        customers = get_customers(db)
        inventory = get_sales_ready_quantities_by_type(db)

    if not customers:
        st.warning("No customers found in the system.")
        st.stop()
    
    if not inventory:
        st.warning("No sales-ready products available.")
        st.stop()
    
    customer_options = {c['customer_name']: c['id'] for c in customers}
    customer_choice = st.selectbox("Select Customer", list(customer_options.keys()))

    st.markdown("#### Select Quantities for Each Product Type")

    select_quantities = {}
    for item in inventory:
        product_type = item['product_type']
        available = item['available_quantity']
        qty = st.number_input(
            label=f"{product_type} (Available: {available})",
            min_value=0,
            max_value=available,
            step=1,
            key=f"qty_{product_type}"
        )
        select_quantities[product_type] = qty

    submitted = st.button("Create Sales Batch", use_container_width=True)
    if submitted:
        st.info("Under Construction")