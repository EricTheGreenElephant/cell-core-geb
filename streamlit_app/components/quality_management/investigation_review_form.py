import streamlit as st
from services.quality_management_services import get_investigated_products, sort_qm_reviewed_products, resolve_investigation
from constants.general_constants import INVESTIGATION_RESOLUTION_OPTIONS
from db.orm_session import get_session
import time


def render_investigation_review():
    st.subheader("Products Under Investigation")

    user_id = st.session_state.get("user_id")

    try:
        with get_session() as db:
            products = get_investigated_products(db)

        if not products:
            st.info("No products are currently under investigation.")
            return
        
        for prod in products:
            with st.expander(f"Product #{prod.product_id} - {prod.sku} - {prod.sku_name}"):
                st.write(f"**Current Stage:** {prod.current_stage_name}")
                st.write(f"**Previous stage:** `{prod.previous_stage_name or 'Unknown'}`")
                st.write(f"**Last Updated:** {prod.last_updated_at.date()}")
                st.write(f"**Location:** {prod.location_name or 'N/A'}")
                st.write(f"**Initial QC Result:** {prod.inspection_result or 'N/A'}")
                st.write(f"**Deviation #:** {prod.deviation_number or 'N/A'}")
                st.write(f"**Comment:** {prod.comment or 'N/A'}")
                st.write(f"**Created By:** {prod.created_by}")
                st.write(f"**Created At:** {prod.created_at}")
    
                selected_label = st.radio(
                    "Resolution Action",
                    options=INVESTIGATION_RESOLUTION_OPTIONS.keys(),
                    key=f"resolution_{prod.product_id}"
                )

                action = INVESTIGATION_RESOLUTION_OPTIONS[selected_label]

                resolution_comment = st.text_area(
                    "Resolution Comment (optional but recommended)",
                    max_chars=255,
                    key=f"res_comment_{prod.product_id}"
                )

                submit_key = f"submit_res_{prod.product_id}"
                if st.button("Submit Resolution", key=submit_key):
                    try:
                        with get_session() as db:
                            sort_qm_reviewed_products(
                                db=db,
                                product_id=prod.product_id,
                                stage_name=prod.previous_stage_name or "InInterimStorage",
                                resolution=action,
                                user_id=user_id,
                            )
                            resolve_investigation(
                                db=db,
                                product_id=prod.product_id,
                                resolution=action,
                                user_id=user_id,
                                comment=resolution_comment
                            )
                            db.commit()
                        st.success(f"Product #{prod.product_id} resolved as '{action}'.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error("Failed to resolve investigation.")
                        st.exception(e)
    except Exception as e:
        st.error("Failed to load investigation records.")
        st.exception(e)