import time
import streamlit as st
from services.logistics_services import get_qc_products_needing_storage, assign_storage_to_products, get_post_treatment_products_needing_storage
from services.filament_service import get_storage_locations
from db.orm_session import get_session


LOCATION_STAGE_MAP = {
    "Inventory": "InInterimStorage",        
    "Quarantine": "Quarantine",              
    "Sales": "PostTreatmentStorage",                
    "B-Ware": "InInterimStorage",          
    "Disposed": "Disposed",                       
    "Offsite": "InTreatment",                  
    "Internal Use": "Internal Use"  
}


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
        
        # Allows user to change default selected shelf
        global_override_location = st.selectbox(
            "Optional: Select same shelf for all products.",
            options=locations,
            format_func=lambda loc: f"{loc.location_name} --- {loc.description}",
            index=0,
            key="global_override"
        )
        # Helper to get default index for location dropdown menu
        def get_default_index(selected_override_location_id):
            if selected_override_location_id:
                for idx, loc in enumerate(locations):
                    if loc.id == selected_override_location_id:
                        return idx
                    
            for idx, loc in enumerate(locations):
                if "CellScrew; Inventory" in loc.description:
                    return idx
            return 0
        
        # Build form
        product_selections = {}

        with st.form("assign_storage_form"):
            st.write("Select storage location for each product:")
            
            for prod in products:
                label = f"#{prod.tracking_id} - Prod ID: {prod.harvest_id} - {prod.product_type} ({prod.inspection_result})"

                selected_location = st.selectbox(
                    label,
                    options=locations,
                    format_func=lambda loc: f"{loc.location_name} --- {loc.description}",
                    index=get_default_index(global_override_location.id if global_override_location else None),
                    key=f"loc_{prod.tracking_id}"
                )

                product_selections[prod.tracking_id] = selected_location.id

            submitted = st.form_submit_button("Assign Storage")
            if submitted:
                try:
                    assignments = []
                    location_lookup = {loc.id: loc for loc in locations}
                    for tracking_id, location_id in product_selections.items():
                        # Determine status based on shelf description
                        loc = location_lookup[location_id]
                        new_stage_code = None
                        for keyword, stage_code in LOCATION_STAGE_MAP.items():
                            if keyword in loc.description:
                                new_stage_code = stage_code
                                break
                        
                        if not new_stage_code:
                            new_stage_code = "InInterimStorage"

                        assignments.append((tracking_id, location_id, new_stage_code))
                        user_id = st.session_state.get("user_id")
                    
                    with get_session() as db:
                            assign_storage_to_products(db, assignments, user_id)

                    st.success("Storage assignment complete.")
                    time.sleep(1.5)
                    st.rerun()

                except Exception as e:
                    st.error("Failed to assign storage.")
                    st.exception(e)

    except Exception as e:
        st.error("An error occurred while assigning storage.")
        st.exception(e)
    #     selected_location = st.selectbox("Select Storage Location", list(location_map.keys()))

    #     selected_ids = []
    #     with st.form("assign_storage_form"):
    #         for prod in products:
    #             label = f"#{prod['tracking_id']} - Prod ID: {prod['harvest_id']} - {prod['product_type']} ({prod['inspection_result']})"
    #             if st.checkbox(label, value=False, key=f"chk_{prod['tracking_id']}"):
    #                 selected_ids.append(prod["tracking_id"])

    #         submitted = st.form_submit_button("Assign Storage")
    #         if submitted:
    #             try:
    #                 selected_loc_id = location_map[selected_location]

    #                 with get_session() as db:
    #                     assign_storage_to_products(db, selected_ids, selected_loc_id, status)

    #                 st.success("Storage assignment complete.")
    #                 time.sleep(1.5)
    #                 st.rerun()
    #             except Exception as e:
    #                 st.error("Failed to assign storage.")
    #                 st.exception(e)

    # except Exception as e:
    #     st.error("An error occurred while assigning storage.")
    #     st.exception(e)