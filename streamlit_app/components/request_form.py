import streamlit as st
from data.production import get_product_types, insert_product_request

def render_product_request_form():
    st.markdown("Submit New Product Request")

    product_types = get_product_types()
    product_options = {name: id for id, name in product_types}

    if not product_options:
        st.warning("No product types available. Please check your catalog.")
        return
    
    with st.form("new_product_request_form"):
        product_choice = st.selectbox("Select Product Type", list(product_options.keys()))
        quantity = st.number_input("Quantity to Print", min_value=1, step=1)
        notes = st.text_area("Notes (optional)", max_chars=250)

        submitted = st.form_submit_button("Submit Request")

        if submitted: 
            try:
                user_id = st.session_state.get("user_id")
                if not user_id:
                    st.error("You must be logged in to make a request.")
                    return
                
                product_id = product_options[product_choice]
                insert_product_request(user_id, product_id, quantity, notes)

                st.success("Product request submitted successfully!")
            except Exception as e:
                st.error("Failed to submit request.")
                st.exception(e)