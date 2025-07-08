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
    user_id = st.session_state.get("user_id")
    
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
    eligible_product_ids = [p.product_id for p in eligible_products]

    if eligible_product_ids:
        st.write(f"Eligible for Approval: {len(eligible_product_ids)} product(s).")
        if st.button("Approve All"):
            try:
                with get_session() as db:
                    target_stage_func(db, eligible_product_ids, user_id)
                st.success(f"Approved {len(eligible_product_ids)} product(s).")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Error approving products.")
                st.exception(e)
    
    for p in products:
        with st.expander(f"Product {p.product_id}"):
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
                    f"Approve {p.product_id}",
                    key=f"approve_{p.product_id}"
                ):
                    try:
                        with get_session() as db:
                            target_stage_func(db, [p.product_id], user_id)
                        st.success(f"Product {p.product_id} approved.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error approving product {p.product_id}")
                        st.exception(e)

