import time
import streamlit as st
from services.qc_services import get_completed_post_treatment_qc, update_post_treatment_qc_fields
from db.orm_session import get_session


def render_treatment_qc_edit_form():
    """
    Creates form that allows user to edit QC information.

    - Fetches post-treatment QC products
    - Creates form to allow user to edit selected product
    - On submission
        - Updates audit_log table
        - Updates post_treatment_inspections table
        - If quarantine:
            - Updates product_tracking
            - Updates product_status_history
            - Inserts record into quarantined_products
    """
    st.subheader("Edit Post-Treatment QC Records")

    with get_session() as db:
        records = get_completed_post_treatment_qc(db)

    if not records:
        st.info("No completed post-treatment QC records found.")
        return
    
    options = {
        f"#{r['inspection_id']} - Prod ID: {r['product_id']} - {r['product_type']} @ {r['inspected_at']}": r
        for r in records
    }

    selected_label = st.selectbox("Select Inspection Record to Edit", list(options.keys()))
    selected = options[selected_label]

    surface = st.checkbox("Surface Treated", value=selected["surface_treated"])
    sterilized = st.checkbox("Sterilized", value=selected["sterilized"])
    visual_pass = st.radio("Visual Pass", [True, False], index=0 if selected["visual_pass"] else 1)
    qc_result = st.selectbox(
        "QC Result",
        options=["Passed", "B-Ware", "Quarantine", "Waste"],
        index=["Passed", "B-Ware", "Quarantine", "Waste"].index(selected["qc_result"])
    )

    if qc_result == "Quarantine":
        q_reason = st.text_area("Reason for Quarantine", max_chars=255).strip()
    else: 
        q_reason = ""

    reason = st.text_area("Reason for Edit", max_chars=255).strip()

    if st.button("Submit QC Update"):

        if qc_result == "Quarantine":
            if not q_reason:
                st.warning("A reason for Quarantine status required.")
                return
            
        if not reason:
            st.warning("A reason for the change is required.")
            return
        
        updates = {}
        if selected["surface_treated"] != surface:
            updates["surface_treated"] = (selected["surface_treated"], surface)
        if selected["sterilized"] != sterilized:
            updates["sterilized"] = (selected["sterilized"], sterilized)
        if selected["visual_pass"] != visual_pass:
            updates["visual_pass"] = (selected["visual_pass"], visual_pass)
        if selected["qc_result"] != qc_result:
            updates["qc_result"] = (selected["qc_result"], qc_result)
        
        if not updates:
            st.info("No changes detected.")
            return
        
        try:
            with get_session() as db:
                update_post_treatment_qc_fields(
                    db=db,
                    inspection_id=selected["inspection_id"],
                    product_id=selected["product_id"],
                    updates=updates,
                    reason=reason,
                    q_reason=q_reason,
                    user_id=st.session_state["user_id"]
                )
            st.success("Post-treatment QC record updated successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to update QC record.")
            st.exception(e)