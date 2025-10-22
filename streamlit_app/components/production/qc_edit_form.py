import time
import streamlit as st
from db.orm_session import get_session
from services.qc_services import get_completed_qc_products, update_qc_fields


def render_qc_edit_form():
    st.subheader("Edit Completed Product QC")

    with get_session() as db:
        qc_records = get_completed_qc_products(db)

    if not qc_records:
        st.info("No completed QC records found.")
        return
    
    options = {
        f"QC #{r['qc_id']} - {r['product_id']} - {r['sku']} - {r['sku_name']} (Lot: {r['lot_number']}) @ {r['print_date']}": r
        for r in qc_records
    }

    selected_label = st.selectbox("Select QC Record to Edit", list(options.keys()))
    selected = options[selected_label]

    weight = st.number_input("Weight (g)", min_value=0.0, format="%.2f", value=float(selected["weight_grams"]))
    pressure = st.number_input("Pressure Drop", min_value=0.0, format="%.2f", value=float(selected["pressure_drop"]))
    visual_pass = st.radio("Visual Pass", [True, False], index=0 if selected["visual_pass"] else 1)
    result = st.selectbox("Inspection Result", ["Passed", "B-Ware", "Quarantine", "Waste"], index=["Passed", "B-Ware", "Quarantine", "Waste"].index(selected["inspection_result"]))
    notes = st.text_area("Notes", max_chars=255, value=selected["notes"] or "").strip()
    reason = st.text_area("Reason for Edit", max_chars=255).strip()

    if st.button("Update QC Record"):
        if not reason:
            st.warning("A reason is required for the update.")
            return
        
        updates = {}
        if selected["weight_grams"] != weight:
            updates["weight_grams"] = (selected["weight_grams"], weight)
        if selected["pressure_drop"] != pressure:
            updates["pressure_drop"] = (selected["pressure_drop"], pressure)
        if selected["visual_pass"] != visual_pass:
            updates["visual_pass"] = (selected["visual_pass"], visual_pass)
        if selected["inspection_result"] != result:
            updates["inspection_result"] = (selected["inspection_result"], result)
        if (selected["notes"] or "") != notes:
            updates["notes"] = (selected["notes"], notes)
        
        if not updates:
            st.info("No changes detected.")
            return
        
        try:
            with get_session() as db:
                update_qc_fields(
                    db=db,
                    qc_id=selected["qc_id"],
                    product_id=selected["id"],
                    updates=updates,
                    reason=reason,
                    user_id=st.session_state["user_id"]
                )
            st.success("QC record updated successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to update QC record.")
            st.exception(e)
        