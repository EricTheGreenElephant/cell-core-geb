import time
import streamlit as st
from services.logistics_services import get_qc_products_needing_storage, assign_storage_to_products, get_post_treatment_products_needing_storage
from services.filament_service import get_storage_locations
from db.orm_session import get_session

def render_storage_assignment_form():
    st.subheader("Assign Storage Location to Printed Bottles")

    mode = st.selectbox(
        "Select Storage Assignment Mode",
        options=["Post-Harvest QC", "Post-Treatment QC"]
    )

    try:
        with get_session() as db:
            if mode == "Post-Harvest QC":
                products = get_qc_products_needing_storage(db)
            else:
                products = get_post_treatment_products_needing_storage(db)

            if not products:
                st.info("No printed bottles require storage.")
                return 
        
            locations = get_storage_locations(db)
        if not locations:
            st.warning("No storage locations available.")
            return
        
        location_map = {
            f"{loc.location_name} --- Description: {loc.description}": loc.id
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
                try:
                    selected_loc_id = location_map[selected_location]
                    selected_desc = next((loc.description or '').lower() for loc in locations if loc.id == selected_loc_id)

                    # Set status based on description
                    if "quarantine" in selected_desc:
                        status = "In Quarantine"
                    else:
                        status = "In Interim Storage"

                    with get_session() as db:
                        assign_storage_to_products(db, selected_ids, selected_loc_id, status)

                    st.success("Storage assignment complete.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Failed to assign storage.")
                    st.exception(e)

    except Exception as e:
        st.error("An error occurred while assigning storage.")
        st.exception(e)