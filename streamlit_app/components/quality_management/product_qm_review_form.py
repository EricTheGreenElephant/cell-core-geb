import streamlit as st
import time
from services.quality_management_services import (
    get_qm_review_products, 
    get_post_treatment_qm_candidates, 
    approve_products_for_treatment, 
    approve_products_for_sales
)
from db.orm_session import get_session


def render_product_qm_review():
    st.subheader("Product QM Approval")

    approval_type = st.selectbox(
        "Select QM Approval Type:",
        options=["Post-Harvest Approval", "Post-Treatment Approval"]
    )

    if approval_type == "Post-Harvest Approval":
        stage_label = "Stored; Pending QM Approval for Treatment"
        target_stage_func = approve_products_for_treatment

        try: 
            with get_session() as db:
                products = get_qm_review_products(db)
        except Exception as e:
            st.error("Failed to load Post-Harvest products.")
            st.exception(e)
            return
    else:
        stage_label = "Stored; Pending QM Approval for Sales"
        target_stage_func = approve_products_for_sales
        try:
            with get_session() as db:
                products = get_post_treatment_qm_candidates(db)
        except Exception as e:
            st.error("Failed to load Post-Treatment products.")
            st.exception(e)
            return
        
    if not products:
        st.info("No products found for QM review.")
        return
    
    data_rows = [p.model_dump() for p in products]
    st.dataframe(data_rows, use_container_width=True)

    eligible_products = [
        p for p in products if p.current_stage_name == stage_label
    ]
    eligible_tracking_ids = [p.tracking_id for p in eligible_products]

    if eligible_tracking_ids:
        st.write(f"Eligible for Approval: {len(eligible_tracking_ids)} product(s).")
        if st.button("Approve All"):
            try:
                user_id = st.session_state.get("user_id")
                 
                with get_session() as db:
                    target_stage_func(db, eligible_tracking_ids, user_id)
                st.success(f"Approved {len(eligible_tracking_ids)} product(s).")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Error approving products.")
                st.exception(e)
    
    for p in products:
        with st.expander(f"Product {p.tracking_id}"):
            st.write(f"Current Stage: {p.current_stage_name}")
            st.write(f"Product Type: {p.product_type_name}")
            st.write(f"Inspection Result: {p.inspection_result}")

            if approval_type == "Post-Treatment Approval":
                st.write(f"Visual Pass: {p.visual_pass}")
                st.write(f"Surface Treated: {p.surface_treated}")
                st.write(f"Sterilized: {p.sterilized}")
            
            st.write(f"Location: {p.current_location}")

            if p.current_stage_name == stage_label:
                if st.button(
                    f"Approve {p.tracking_id}",
                    key=f"approve_{p.tracking_id}"
                ):
                    try:
                        with get_session() as db:
                            target_stage_func(db, [p.tracking_id])
                        st.success(f"Product {p.tracking_id} approved.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error approving product {p.tracking_id}")
                        st.exception(e)

    #     st.dataframe([p.model_dump() for p in products])

    #     products_in_storage = [p for p in products if p.current_stage_name == "Stored; Pending QM Approval for Treatment"]
    #     tracking_ids_in_storage = [p.tracking_id for p in products_in_storage]

    #     if tracking_ids_in_storage:
    #         if st.button("Approve All for Treatment", type="primary"):
    #             try:
    #                 with get_session() as db:
    #                     approve_products_for_treatment(db, tracking_ids_in_storage)
    #                 st.success(f"Approved {len(tracking_ids_in_storage)} product(s) for treatment.")
    #                 st.rerun()
    #             except Exception as e:
    #                 st.error("Error approving products.")
    #                 st.exception(e)
        
    #     st.divider()
    #     st.subheader("Approve Products Individually")
    #     for product in products:
    #         with st.expander(f"Product {product.tracking_id}"):
    #             st.write(f"Harvest ID: {product.harvest_id}")
    #             st.write(f"Current Stage: {product.current_stage_name}")
    #             st.write(f"Product Type: {product.product_type_name}")
    #             st.write(f"QC Result: {product.inspection_result}")
    #             st.write(f"Storage Location: {product.current_location}")
    #             st.write(f"QC Notes: {product.qc_notes}")

    #             if product.current_stage_name == "Stored; Pending QM Approval for Treatment":
    #                 if st.button(f"Approve {product.tracking_id} for Treatment", type="primary", key=f"approve_{product.tracking_id}"):
    #                     try:
    #                         with get_session() as db:
    #                             approve_products_for_treatment(db, [product.tracking_id])
    #                         st.success(f"Product {product.tracking_id} approved for Treatment.")
    #                         st.rerun()
    #                     except Exception as e:
    #                         st.error(f"Erro approving product {product.tracking_id}.")
    #                         st.exception(e)
    
    # except Exception as e:
    #     st.error("An error occurred while loading Product QM Review data.")
    #     st.exception(e)