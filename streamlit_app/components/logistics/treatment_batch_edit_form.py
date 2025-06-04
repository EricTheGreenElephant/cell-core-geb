import time
import streamlit as st
from db.orm_session import get_session
from services.logistics_services import (
    get_shipped_batches, 
    get_products_by_batch_id, 
    remove_product_from_batch, 
    update_treatment_batch_fields
)
from services.audit_services import update_record_with_audit
from schemas.audit_schemas import FieldChangeAudit


def render_treatment_batch_edit_form():
    st.subheader("Edit Treatment Batch Products")

    with get_session() as db:
        batches = get_shipped_batches(db)

    if not batches:
        st.info("No treatment batches found for editing.")
        return
    
    batch_map = {f"Batch #{b['id']} - {b['sent_at'].date()}": b["id"] for b in batches}
    batch_label = st.selectbox("Select Treatment Batch", list(batch_map.keys()), key="edit_batch_select")
    batch_id = batch_map[batch_label]

    with get_session() as db:
        products = get_products_by_batch_id(db, batch_id)

    if not products:
        st.warning("No products found in this batch.")
        return
    
    for idx, p in enumerate(products):
        with st.expander(f"Product #{p['tracking_id']} - {p['product_type']} - {p['inspection_result']}"):
            surface_treat = st.checkbox("Surface Treat", value=p["surface_treat"], key=f"st_{idx}")
            sterilized = st.checkbox("Sterilize", value=p["sterilize"], key=f"ster_{p['tracking_id']}_{p['id']}_{idx}")
            reason = st.text_area("Reason for Update", max_chars=255, key=f"rsn_{idx}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update Product", key=f"btn_upd_{idx}"):
                    if not reason.strip():
                        st.warning("A reason is required to perform an update.")
                        return

                    updates = {}
                    if p["surface_treat"] != surface_treat:
                        updates["surface_treat"] = (p["surface_treat"], surface_treat)
                    if p["sterilize"] != sterilized:
                        updates["sterilize"] = (p["sterilize"], sterilized)
                    
                    if not updates:
                        st.info("No changes detected.")
                        return
                    
                    try:
                        with get_session() as db:
                            update_treatment_batch_fields(
                                db=db, 
                                batch_product_id=p["id"],
                                updates=updates,
                                reason=reason,
                                user_id=st.session_state["user_id"]
                            )
                        st.success("Treatment batch product updated successfully.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error("Failed to update treatment batch product.")
                        st.exception(e)
            with col2:
                if st.button("Remove from Batch", key=f"btn_rm_{idx}"):
                    confirm = st.checkbox("Confirm removal", key=f"cnf_rm_{idx}")
                    if confirm:
                        try:
                            with get_session() as db:
                                remove_product_from_batch(
                                    db=db, 
                                    batch_product_id=p["id"],
                                    product_id=p["tracking_id"],
                                    user_id=st.session_state["user_id"],
                                    reason=reason
                                )
                            st.success("Product removed from batch.")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error("Failed to remove product from batch.")
                            st.exception(e)
