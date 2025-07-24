import streamlit as st
from services.quality_management_services import (
    get_quarantined_products, 
    escalate_to_investigation, 
    sort_qm_reviewed_products,
    resolve_quarantine_record
)
from schemas.quality_management_schemas import InvestigationEntry
from db.orm_session import get_session
import time


RESOLUTION_OPTIONS = {
    "Approve as A-Ware": "Passed",
    "Approve as B-Ware": "B-Ware",
    "Mark as Waste": "Waste",
    "Under Investigation": "Investigation",
}

def render_quarantine_review_form():
    st.subheader("Quarantine Product Review")

    user_id = st.session_state.get("user_id")

    try:
        with get_session() as db:
            products = get_quarantined_products(db)

        if not products:
            st.info("No products currently in quarantine.")
            return

        for prod in products:
            with st.expander(f"Product #{prod.product_id} - {prod.product_type}"):
                # === Quarantine Info ===
                st.write(f"**Quarantined At:** {prod.quarantine_date.strftime('%Y-%d-%m %H:%M')}")
                st.write(f"**Quarantined By:** {prod.quarantined_by}")
                st.write(f"**Reason for Quarantine:** {prod.quarantine_reason or 'N/A'}")
                # === Product Lifecycle Info ===
                st.write(f"**Previous Stage:** {prod.previous_stage_name or 'Unknown'}")
                st.write(f"**Stage:** {prod.current_stage_name}")
                st.write(f"**Last Updated:** {prod.last_updated_at.date()}")
                st.write(f"**Location:** {prod.location_name or 'N/A'}")
                # === QC Info ===
                st.write(f"**Post-Harvest QC Result:** {prod.inspection_result}")
                st.write(f"**Post-Treatment QC Result:** {prod.qc_result}")

                # === Decision ===
                selected_label = st.radio(
                    "Action",
                    options=RESOLUTION_OPTIONS.keys(),
                    key=f"action_{prod.product_id}"
                )
                
                action = RESOLUTION_OPTIONS[selected_label]

                comment = deviation = ""

                comment = st.text_area("Comment", max_chars=255, key=f"comment_{prod.product_id}")

                if action == "Investigation":
                    deviation = st.text_input("Deviation Number", key=f"dev_{prod.product_id}")
                
                submit_key = f"submit_{prod.product_id}"
                if st.button("Submit Decision", key=submit_key):
                    if not comment:
                        st.error("Comment required for resolution.")
                        return
                    try:
                        with get_session() as db:
                            if action == "Investigation":
                                if not deviation:
                                    st.warning("Deviation Number Required!")
                                    return
                                
                                entry = InvestigationEntry(
                                    product_id=prod.product_id,
                                    deviation_number=deviation,
                                    comment=comment,
                                    created_by=user_id
                                )

                                escalate_to_investigation(db, entry)
                            
                            else:
                                # === Update Product Stage and QC ===
                                sort_qm_reviewed_products(
                                    db=db,
                                    product_id=prod.product_id,
                                    stage_name=prod.previous_stage_name,
                                    resolution=action,
                                    user_id=user_id
                                )

                                # === Resolve Quarantine Record ===
                                resolve_quarantine_record(
                                    db=db,
                                    product_id=prod.product_id,
                                    result=action,
                                    resolved_by=user_id,
                                    comment=comment
                                )
                            db.commit()

                        st.success(f"Action '{action}' submitted for product #{prod.product_id}.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error("Failed to submit decision.")
                        st.exception(e)
    except Exception as e:
        st.error("Unable to load quarantined products.")
        st.exception(e)