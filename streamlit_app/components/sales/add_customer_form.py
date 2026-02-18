import streamlit as st
from db.orm_session import get_session
from services.sales_services import create_customer, get_customers


def render_add_customer_form():
    st.subheader("Add Customer")

    with st.form("add_customer_form", clear_on_submit=True):
        name = st.text_input("Customer identifier", max_chars=50)
        submitted = st.form_submit_button("Add Customer")

    if not submitted:
        with get_session() as db:
            customers = get_customers(db)
        if customers:
            st.caption("Existing customers")
            st.dataframe(customers, width="stretch", hide_index=True)
        return
    
    cleaned = (name or "").strip()
    if not cleaned:
        st.error("Please enter a customer name.")
        return
    
    try:
        with get_session() as db:
            new_id = create_customer(db, cleaned)
        st.success(f"Customer added: {cleaned} (id={new_id})")

        with get_session() as db:
            customers = get_customers(db)
        st.dataframe(customers, use_container_width=True, hide_index=True)

    except ValueError as e:
        st.warning(str(e))
    except Exception as e:
        st.error(f"Failed to add customer: {e}")