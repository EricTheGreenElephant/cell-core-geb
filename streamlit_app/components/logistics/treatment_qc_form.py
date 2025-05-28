import time 
import streamlit as st
from random import sample
from services.logistics_services import (
    get_shipped_batches,
    get_products_by_batch_id,
    update_post_treatment_qc,
    mark_batch_as_inspected
)
from db.orm_session import get_session


color_map = {
    "QM Request": "green",
    "Internal Use": "orange",
    "Waste": "red"
}

def determine_qc_result(prior_result, surface_treat_required, surface_treated, sterilized, visual_pass):
    if not sterilized or not visual_pass:
        return "Waste"
    if surface_treat_required and not surface_treated:
        return "Waste"
    if prior_result == "Passed" and surface_treated and sterilized and visual_pass:
        return "QM Request"
    return "Internal Use"
    
def render_treatment_qc_form():
    st.subheader("Treatment Quality Control")

    try:
        with get_session() as db:
            batches = get_shipped_batches(db)
        if not batches:
            st.info("No returned batches available for inspection.")
            return
        
        batch_options = {f"Batch #{b['id']} - {b['sent_at'].date()}": b['id'] for b in batches}
        selected_label = st.selectbox("Select Treatment Batch", list(batch_options.keys()))
        batch_id = batch_options[selected_label]

        with get_session() as db:
            products = get_products_by_batch_id(db, batch_id)

        total = len(products)
        sample_size = max(2, round(0.05 * total))
        # Sets the random sample to prevent re-randomizing product selection when user changes visual pass option
        sample_key = f"sample_batch_{batch_id}"
        if sample_key not in st.session_state:
            st.session_state[sample_key] = sample(products, sample_size)
        random_sample = st.session_state[sample_key]

        st.markdown(f"**Randomly Selected for Visual Inspection: {sample_size} of {total} products**")

        failed_sample = False
        sample_visual_results = {}
        for i, p in enumerate(random_sample):
            if p["inspection_result"] == 'B-Ware':
                inspection_result = 'B-Ware'
            else:
                inspection_result = 'A-Ware'
            st.markdown(f"**Sample #{i+1}: Product #{p['tracking_id']} - {p['product_type']}: {inspection_result}**")
            p["visual_pass"] = st.radio(
                f"Visual Pass (Product #{p['tracking_id']})", [True, False], horizontal=True, key=f"vis_{p['tracking_id']}"
            )
            sample_visual_results[p["tracking_id"]] = p["visual_pass"]
            if not p['visual_pass']:
                failed_sample = True
        
        st.divider()
        st.markdown("### Full Inspection")

        full_qc = []
        for p in products:
            if p["inspection_result"] == 'B-Ware':
                inspection_result = 'B-Ware'
            else:
                inspection_result = 'A-Ware'
            st.markdown(f"**Product #{p['tracking_id']} - {p['product_type']}: {inspection_result}**")

            surface = st.checkbox("Surface Treated", value=p["surface_treat"], key=f"surf_{p['tracking_id']}")
            sterilized = st.checkbox("Sterilized", value=p["sterilize"], key=f"ster_{p['tracking_id']}")

            visual = None
            if failed_sample:
                default_vis = sample_visual_results.get(p["tracking_id"], True)
                visual = st.radio(
                    "Visual Pass", [True, False], index=0 if default_vis else 1, horizontal=True, key=f"full_vis_{p['tracking_id']}"
                )
            
            prior_result = p["inspection_result"]
            treat_required = p["surface_treat"]
            visual_val = visual if visual is not None else True

            qc_result = determine_qc_result(prior_result, treat_required, surface, sterilized, visual_val)
            color = color_map.get(qc_result, "black")

            st.markdown(f"**Suggested QC Result:** <span style='color:{color}; font-weight:bold'>{qc_result}</span>", unsafe_allow_html=True)
            full_qc.append({
                "tracking_id": p["tracking_id"],
                "surface_treat": surface,
                "sterilize": sterilized,
                "visual_pass": visual_val,
                "qc_result": qc_result
            })

        if st.button("Finalize Inspection"):
            try:
                inspector = st.session_state.get("user_id")
                with get_session() as db:
                    update_post_treatment_qc(db, full_qc, inspector)
                    mark_batch_as_inspected(db, batch_id)
                st.success("Treatment QC completed successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to complete QC.")
                st.exception(e)
    
    except Exception as e:
        st.error("Unable to load treatment batches.")
        st.exception(e)