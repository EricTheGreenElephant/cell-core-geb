import streamlit as st
import time
from services.sales_services import get_customers, get_active_sales_catalogue, get_orderable_product_types, create_sales_order, get_active_supplements
from schemas.sales_schemas import SalesOrderInput
from db.orm_session import get_session
from collections import defaultdict


def render_sales_order_form():
    st.subheader("Create Sales Order")

    with get_session() as db:
        customers = get_customers(db)
        catalogues = get_active_sales_catalogue(db)
        product_types = get_orderable_product_types(db)
        supplements = get_active_supplements(db)

    if not customers:
        st.warning("No customers found.")
        return
    
    if not catalogues:
        st.warning("No active catalogue packages found.")
        return
    
    if not product_types:
        st.warning("No product types found.")
        return
    
    if not supplements:
        st.warning("No supplement items found.")
        return
    
    product_lookup = {p.id: p.name for p in product_types}
    supplement_lookup = {s.id: s.name for s in supplements}

    customer_options = {c["customer_name"]: c["id"] for c in customers}
    customer_choice = st.selectbox("Select Customer", list(customer_options.keys()))

    st.markdown("#### Select Catalogue Packages and Quantities")

    package_quantities = {}
    for cat in catalogues:
        with st.expander(f"{cat.package_name} (${cat.price:.2f})"):
            st.markdown(f"*{cat.package_desc}*")
            qty = st.number_input(
                label="Quantity",
                min_value=0,
                step=1,
                key=f"catalogue_{cat.id}"
            )
            package_quantities[cat.id] = qty
    
    product_quantites = defaultdict(int)
    supplement_quantities = defaultdict(int)

    for cat in catalogues:
        count = package_quantities.get(cat.id, 0)
        if count == 0:
            continue

        for p in cat.products:
            product_quantites[p.product_id] += p.product_quantity * count
        for s in cat.supplements:
            supplement_quantities[s.supplement_id] += s.supplement_quantity * count

    if any(package_quantities.values()):
        st.markdown("#### Summary of Order Quantities")
        st.markdown("**Products:**")
        for pid, qty in product_quantites.items():
            name = product_lookup.get(pid, f"Unknown Product ({pid})")
            st.markdown(f"- {name}: {qty}")

        if supplement_quantities:
            st.markdown("**Supplements:**")
            for sid, qty in supplement_quantities.items():
                name = supplement_lookup.get(sid, f"Uknown Supplement ({sid})")
                st.markdown(f"- {name}: {qty}")
    
    notes = st.text_area("Order Notes (Optional)", max_chars=255).strip()

    submitted = st.button("Create Sales Order", use_container_width=True)

    if submitted:
        user_id = st.session_state.get("user_id")

        data = SalesOrderInput(
            customer_id=customer_options[customer_choice],
            created_by=user_id,
            updated_by=user_id,
            product_quantities=dict(product_quantites),
            supplement_quantities=dict(supplement_quantities),
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