import time
import streamlit as st
from services.logistics_services import (
    get_qc_products_needing_storage, 
    assign_storage_to_products, 
    get_post_treatment_products_needing_storage,
    get_adhoc_products_needing_storage
)
from services.filament_service import get_storage_locations
from constants.storage_constants import NEXT_STAGE_BY_RESULT, SHELF_OPTIONS_BY_RESULT
from constants.product_status_constants import STATUS_MAP_QC_TO_BUSINESS
from db.orm_session import get_session


def render_storage_assignment_form():
    """
    Creates form that requires user to assign storage shelf to products

    - User selects for post-harvest or post-treatment
    - Fetches products based on selection
    - Fetches available storage locations
    - Imports stage and location constants to match product qc result to required location
    - Updates product_tracking location_id to input location
    """
    st.subheader("Assign Storage Location")

    mode = st.selectbox(
        "Select Storage Assignment Mode",
        options=["Post-Harvest QC", "Post-Treatment QC", "AdHoc Quarantine"]
    )

    try:
        with get_session() as db:
            if mode == "Post-Harvest QC":
                products = get_qc_products_needing_storage(db)
            elif mode == "Post-Treatment QC":
                products = get_post_treatment_products_needing_storage(db)
            else:
                products = get_adhoc_products_needing_storage(db)

            locations = get_storage_locations(db)

        if not products:
            st.info("No products require storage.")
            return
        
        if not locations:
            st.warning("No storage locations available.")
            return
        
        product_selections = {}

        with st.form("assign_storage_form"):
            st.write("Assign storage for each product:")

            for prod in products:
                product_status = prod.inspection_result

                business_status = STATUS_MAP_QC_TO_BUSINESS.get(product_status, "A-Ware")

                allowed_keywords = SHELF_OPTIONS_BY_RESULT.get(business_status, {}).get(mode, [])
                valid_shelves = [
                    loc for loc in locations
                    if any(keyword in loc.description for keyword in allowed_keywords)
                ]

                label = f"#{prod.product_id} - {prod.product_type} ({business_status})"
                selected_shelf = st.selectbox(
                    label,
                    options=valid_shelves,
                    format_func=lambda loc: f"{loc.location_name} --- {loc.description}",
                    key=f"shelf_{prod.product_id}"
                )

                next_stage_code = NEXT_STAGE_BY_RESULT[business_status][mode]

                product_selections[prod.product_id] = (selected_shelf.id, next_stage_code)

            submitted = st.form_submit_button("Assign Storage")
            if submitted:
                try:
                    user_id = st.session_state.get("user_id")
                    assignments = [
                        (pid, loc_id, stage_code)
                        for pid, (loc_id, stage_code) in product_selections.items()
                    ]
                    update_stage = False if mode == "AdHoc Quarantine" else True
                    
                    with get_session() as db:
                        assign_storage_to_products(db, assignments, user_id, update_stage=update_stage)

                    st.success("Storage assignment complete.")
                    time.sleep(1.5)
                    st.rerun()

                except Exception as e:
                    st.error("Failed to assign storage.")
                    st.exception(e)
                
    except Exception as e:
        st.error("An error occurred while assigning storage.")
        st.exception(e)
