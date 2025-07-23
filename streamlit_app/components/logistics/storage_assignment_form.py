import time
import streamlit as st
from services.logistics_services import get_qc_products_needing_storage, assign_storage_to_products, get_post_treatment_products_needing_storage
from services.filament_service import get_storage_locations
from constants.storage_constants import NEXT_STAGE_BY_RESULT, SHELF_OPTIONS_BY_RESULT
from constants.product_status_constants import STATUS_MAP_QC_TO_BUSINESS
from db.orm_session import get_session


def render_storage_assignment_form():
    st.subheader("Assign Storage Location")

    mode = st.selectbox(
        "Select Storage Assignment Mode",
        options=["Post-Harvest QC", "Post-Treatment QC"]
    )

    try:
        with get_session() as db:
            products = (
                get_qc_products_needing_storage(db)
                if mode == "Post-Harvest QC"
                else get_post_treatment_products_needing_storage(db)
            )
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

# LOCATION_STAGE_MAP = {
#     "Inventory": "InInterimStorage",        
#     "Quarantine": "Quarantine",              
#     "Sales": "PostTreatmentStorage",                
#     "B-Ware": "InInterimStorage",          
#     "Disposed": "Disposed",                       
#     "Offsite": "InTreatment",                  
#     "Internal Use": "Internal Use"  
# }


# def render_storage_assignment_form():
#     st.subheader("Assign Storage Location to Printed Bottles")

#     mode = st.selectbox(
#         "Select Storage Assignment Mode",
#         options=["Post-Harvest QC", "Post-Treatment QC"]
#     )

#     try:
#         with get_session() as db:
#             if mode == "Post-Harvest QC":
#                 products = get_qc_products_needing_storage(db)
#             else:
#                 products = get_post_treatment_products_needing_storage(db)

#             if not products:
#                 st.info("No printed bottles require storage.")
#                 return 
        
#             locations = get_storage_locations(db)
#         if not locations:
#             st.warning("No storage locations available.")
#             return
        
#         # Allows user to change default selected shelf
#         global_override_location = st.selectbox(
#             "Optional: Select same shelf for all products.",
#             options=locations,
#             format_func=lambda loc: f"{loc.location_name} --- {loc.description}",
#             index=0,
#             key="global_override"
#         )
#         # Helper to get default index for location dropdown menu
#         def get_default_index(selected_override_location_id):
#             if selected_override_location_id:
#                 for idx, loc in enumerate(locations):
#                     if loc.id == selected_override_location_id:
#                         return idx
                    
#             for idx, loc in enumerate(locations):
#                 if "CellScrew; Inventory" in loc.description:
#                     return idx
#             return 0
        
#         # Build form
#         product_selections = {}

#         with st.form("assign_storage_form"):
#             st.write("Select storage location for each product:")
            
#             for prod in products:
#                 label = f"#{prod.product_id} - Prod ID: {prod.harvest_id} - {prod.product_type} ({prod.inspection_result})"

#                 selected_location = st.selectbox(
#                     label,
#                     options=locations,
#                     format_func=lambda loc: f"{loc.location_name} --- {loc.description}",
#                     index=get_default_index(global_override_location.id if global_override_location else None),
#                     key=f"loc_{prod.product_id}"
#                 )

#                 product_selections[prod.product_id] = selected_location.id

#             submitted = st.form_submit_button("Assign Storage")
#             if submitted:
#                 try:
#                     assignments = []
#                     location_lookup = {loc.id: loc for loc in locations}
#                     for product_id, location_id in product_selections.items():
#                         # Determine status based on shelf description
#                         loc = location_lookup[location_id]
#                         new_stage_code = None
#                         for keyword, stage_code in LOCATION_STAGE_MAP.items():
#                             if keyword in loc.description:
#                                 new_stage_code = stage_code
#                                 break
                        
#                         if not new_stage_code:
#                             new_stage_code = "InInterimStorage"

#                         assignments.append((product_id, location_id, new_stage_code))
#                         user_id = st.session_state.get("user_id")
                    
#                     with get_session() as db:
#                             assign_storage_to_products(db, assignments, user_id)

#                     st.success("Storage assignment complete.")
#                     time.sleep(1.5)
#                     st.rerun()

#                 except Exception as e:
#                     st.error("Failed to assign storage.")
#                     st.exception(e)

#     except Exception as e:
#         st.error("An error occurred while assigning storage.")
#         st.exception(e)
