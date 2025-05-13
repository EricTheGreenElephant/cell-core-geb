import time
import streamlit as st
from data.logistics import get_qc_passed_products, create_treatment_batch


def render_logistics_form():
    st.subheader("📦 Create Treatment Batch")

    user_id = st.session_state.get("user_id")

    try:
        products = get_qc_passed_products()

        if not products:
            st.info("No products available for treatment.")
            return
        
        options = [
            {
                "Tracking ID": p["tracking_id"],
                "Current Status": p["current_status"],
                "Harvest ID": p["harvest_id"],
                "Product Type": p["product_type"],
                "Location": p["location_name"],
                "QC Result": p["inspection_result"],
                "Include": True
            }
            for p in products
        ]

        edited = st.data_editor(
            options,
            use_container_width=True,
            disabled=["Tracking ID", "Current Status", "Harvest ID", "Product Type", "Location", "QC Result", ],
            column_config={
                "Include": st.column_config.CheckboxColumn("Include in Batch")
            },
            hide_index=True
        )

        to_include = [p for p in edited if p["Include"]]

        notes = st.text_area("Optional Notes", max_chars=250)

        if st.button("Create Treatment Batch") and to_include:
            tracking_ids = [p["Tracking ID"] for p in to_include]
            create_treatment_batch(user_id, tracking_ids, notes)
            st.success("Treatment batch created successfully.")
            time.sleep(1.5)
            st.rerun()
    
    except Exception as e:
        st.error("Failed to load products.")
        st.exception(e)
