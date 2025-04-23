import streamlit as st
from data.logistics import get_qc_passed_products, create_treatment_batch


def render_logistics_form():
    st.subheader("📦 Create Treatment Batch")

    user_id = st.session_state.get("user_id")
    products = get_qc_passed_products()

    if not products:
        st.info("No QC-passed products available for treatment.")
        return
    
    options = {
        f"#{p['tracking_id']} - {p['product_type']} (Lot: {p['lot_number']})": p["tracking_id"]
        for p in products
    }

    selected = st.multiselect("Select Products to Include in Treatment Batch", options.keys())

    notes = st.text_area("Optional Notes", max_chars=250)

    submitted = st.button("Create Treatment Batch")

    if submitted:
        if not selected:
            st.warning("Please select at least one product.")
            return
        try:
            product_ids = [options[s] for s in selected]
            create_treatment_batch(user_id, product_ids, notes)
            st.success(f"Treatment batch created for {len(product_ids)} products.")
        except Exception as e:
            st.error("Failed to create batch.")
            st.exception(e)
