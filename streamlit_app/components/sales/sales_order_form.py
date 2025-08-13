import streamlit as st
import time
from services.sales_services import get_customers, get_orderable_product_types, create_sales_order, get_active_supplements
from schemas.sales_schemas import SalesOrderInput
from db.orm_session import get_session


def render_sales_order_form():
    st.subheader("Create Sales Order")

    with get_session() as db:
        customers = get_customers(db)
        inventory = get_orderable_product_types(db)
        supplements = get_active_supplements(db)

    if not customers:
        st.warning("No customers found in the system.")
        return
    
    if not inventory:
        st.warning("No sales-ready products available.")
        return
    
    if not supplements:
        st.warning("No supplemental items available.")
        return
    
    customer_options = {c['customer_name']: c['id'] for c in customers}
    customer_choice = st.selectbox("Select Customer", list(customer_options.keys()))

    st.markdown("#### Select Quantities for Each Product Type")

    mini_qty_validation = "CS MINI"

    product_quantities = {}
    supplement_quantities = {}
    for product_type in inventory:
        qty = st.number_input(
            label=f"{product_type.name}",
            min_value=0,
            step=1,
            key=f"prod_qty_{product_type.id}"
        )

        # === CS MINI quantity triplicate and accessory addition (optional) ===
        if product_type.name == mini_qty_validation and qty != 0:
            total_qty = qty * 3
            product_quantities[product_type.id] = total_qty
            for supplement in supplements:
                supp_qty = st.number_input(
                    label=f"{supplement.name}",
                    min_value=0,
                    step=1,
                    key=f"supp_qty_{supplement.id}"
                )
                if supp_qty > qty:
                    st.info(f"{supplement.name} quantity more than {product_type.name} quantity - double check.")
                supplement_quantities[supplement.id] = supp_qty
        else:
            product_quantities[product_type.id] = qty
    
    notes = st.text_area("Order Notes (Optional)", max_chars=255).strip()

    submitted = st.button("Create Sales Order", use_container_width=True)
    if submitted:
        user_id = st.session_state.get("user_id")

        data = SalesOrderInput(
            customer_id=customer_options[customer_choice],
            created_by=user_id,
            updated_by=user_id,
            product_quantities=product_quantities,
            supplement_quantities=supplement_quantities,
            notes=notes
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