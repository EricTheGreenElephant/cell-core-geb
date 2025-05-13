import time
import streamlit as st
from data.logistics import get_qc_products_needing_storage, assign_storage_to_products
from data.filament import get_storage_locations


def render_harvest_storage_form():
    st.subheader("Assign Storage Location to Printed Bottles")

    try:
        products = get_qc_products_needing_storage()
        if not products:
            st.info("No printed bottles require storage.")
            return 
        
        locations = get_storage_locations()
        if not locations:
            st.warning("No storage locations available.")
            return
        
        location_map = {
            f"{loc['location_name']} --- Description: {loc['description']}": loc['id']
            for loc in locations
        }
        selected_location = st.selectbox("Select Storage Location", list(location_map.keys()))

        selected_ids = []
        with st.form("assign_storage_form"):
            for prod in products:
                label = f"#{prod['tracking_id']} - Prod ID: {prod['harvest_id']} - {prod['product_type']} ({prod['inspection_result']})"
                if st.checkbox(label, value=False, key=f"chk_{prod['tracking_id']}"):
                    selected_ids.append(prod["tracking_id"])

            submitted = st.form_submit_button("Assign Storage")
            if submitted:
                assign_storage_to_products(selected_ids, location_map[selected_location])
                st.success("Storage assignment complete.")
                time.sleep(1.5)
                st.rerun()

    except Exception as e:
        st.error("An error occurred while assigning storage.")
        st.exception(e)