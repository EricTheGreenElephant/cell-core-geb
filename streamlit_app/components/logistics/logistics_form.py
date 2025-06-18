import time
import streamlit as st
from services.logistics_services import get_qc_passed_products, create_treatment_batch
from schemas.logistics_schemas import TreatmentBatchCreate, TreatmentProductData
from db.orm_session import get_session

def render_logistics_form():
    st.subheader("📦 Create Treatment Batch")

    user_id = st.session_state.get("user_id")

    try:
        with get_session() as db:
            products = get_qc_passed_products(db)

        if not products:
            st.info("No products available for treatment.")
            return
        
        options = [
            {
                "Include": True,
                "Tracking ID": p.tracking_id,
                "Current Status": p.current_stage_name,
                "Harvest ID": p.harvest_id,
                "Product Type": p.product_type,
                "Location": p.location_name,
                "QC Result": p.inspection_result,
                "Surface Treat": True,
                "Sterilize": True
            }
            for p in products
        ]

        edited = st.data_editor(
            options,
            use_container_width=True,
            disabled=["Tracking ID", "Current Status", "Harvest ID", "Product Type", "Location", "QC Result"],
            column_config={
                "Include": st.column_config.CheckboxColumn("Include in Batch"),
                "Surface Treat": st.column_config.CheckboxColumn("Surface Treat"),
                "Sterilize": st.column_config.CheckboxColumn("Sterilize")
            },
            hide_index=True
        )
        # Filter to only selected rows
        to_include = [p for p in edited if p["Include"]]

        notes = st.text_area("Optional Notes", max_chars=250)

        if st.button("Create Treatment Batch") and to_include:
            try:
                tracking_data = [
                    TreatmentProductData(
                        tracking_id=p["Tracking ID"],
                        surface_treat=p["Surface Treat"],
                        sterilize=p["Sterilize"]
                    ) for p in to_include
                ]

                payload = TreatmentBatchCreate(
                    sent_by=user_id,
                    tracking_data=tracking_data,
                    notes=notes
                )

                with get_session() as db:
                    create_treatment_batch(db, payload)

                st.success("Treatment batch created successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("failed to create treatment batch.")
                st.exception(e)
    
    except Exception as e:
        st.error("Failed to load products.")
        st.exception(e)
