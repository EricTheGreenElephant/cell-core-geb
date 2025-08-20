import time 
import streamlit as st
from random import sample
from services.logistics_services import (
    get_shipped_batches,
    get_products_by_batch_id,
    update_post_treatment_qc,
    mark_batch_as_inspected
)
from constants.general_constants import COLOR_MAP
from db.orm_session import get_session


def determine_qc_result(prior_result, surface_treat_required, surface_treated, sterilized, quarantine, visual_pass):
    """
    Helper function to help determine QC result display label

    Parameters
        - prior_result: str
            QC result from post-harvest qc
        - surface_treat_required: bool
            Boolean indication if product required surface treatment
        - surface_treated: bool
            Boolean indication of whether or not product actually received surface treatment
        - sterilized: bool
            Boolean indication of whether or not product actually received sterilization
        - quarantine: bool
            Boolean indication from user if product should be quarantined
        - visual_pass: bool
            Boolean indication of whether or not product passed visual inspection

    Returns
        - String text to display for suggested qc result
    """
    if not sterilized or not visual_pass:
        return "Waste"
    if surface_treat_required and not surface_treated:
        return "Waste"
    if quarantine:
        return "Quarantine"
    if prior_result == "A-Ware" and surface_treated and sterilized and visual_pass:
        return "Passed"
    return "B-Ware"
    
def render_treatment_qc_form():
    """
    Creates form that allows user to provide qc result post-treatment

    - Fetches outstanding shipment batches and products
    - Pulls randomized sample size to check for QC pass/fail
    - If randomized sample fails, all products will have option to pass/fail
    - Allows selection of quarantine
    - On submission
        - treatment_batches table updated to 'inspected'
        - QC record inserted into post_treatment_inspections
        - If quarantined, record inserted into quarantined_products table
        - Updates product_tracking product stage and product_status_history tables
    """
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
        actual_sample_size = min(sample_size, total)

        mode_key = f"inspection_mode_{batch_id}"
        inspection_mode = st.radio(
            "Inspection Mode",
            options=["Random sample (≈5%)", "Inspect all products (override)"],
            index=0,
            horizontal=True,
            key=mode_key,
            help="Choose 'Inspect all products' to force 100% visual inspection (useful for new 3rd-party treatment)."
        )
        override_all = inspection_mode == "Inspect all products (override)"

        failed_sample = False
        sample_visual_results = {}

        if not override_all:
            # Sets the random sample to prevent re-randomizing product selection when user changes visual pass option
            sample_key = f"sample_batch_{batch_id}"
            if sample_key not in st.session_state:
                st.session_state[sample_key] = sample(products, actual_sample_size)
            random_sample = st.session_state[sample_key]

            st.markdown(f"**Randomly Selected for Visual Inspection: {sample_size} of {total} products**")


            for i, p in enumerate(random_sample):
                if p["current_status"] == 'B-Ware':
                    inspection_result = 'B-Ware'
                else:
                    inspection_result = 'A-Ware'
                st.markdown(f"**Sample #{i+1}: Product #{p['product_id']} - {p['product_type']}: {inspection_result}**")
                p["visual_pass"] = st.radio(
                    f"Visual Pass (Product #{p['product_id']})", [True, False], horizontal=True, key=f"vis_{p['product_id']}"
                )
                sample_visual_results[p["product_id"]] = p["visual_pass"]
                if not p['visual_pass']:
                    failed_sample = True
        else:
            st.info("Override enabled: 100% visual inspection required for this batch.")
        
        if override_all:
            failed_sample = True

        st.divider()
        st.markdown("### Full Inspection")

        quarantine_all = st.checkbox("Quarantine All", value=False)
        quarantine_all_reason = ""
        if quarantine_all:
            quarantine_all_reason = st.text_area(
                "Reason for Quarantining All Products",
                max_chars=255,
                key="quarantine_all_reason"
            ).strip()

        full_qc = []
        for p in products:
            if p["current_status"] == 'B-Ware':
                inspection_result = 'B-Ware'
            else:
                inspection_result = 'A-Ware'
            st.markdown(f"**Product #{p['product_id']} - {p['product_type']}: {inspection_result}**")

            surface = st.checkbox("Surface Treated", value=p["surface_treat"], key=f"surf_{p['product_id']}")
            sterilized = st.checkbox("Sterilized", value=p["sterilize"], key=f"ster_{p['product_id']}")
            quarantine = st.checkbox("Quarantine", value=quarantine_all, key=f"quar_{p['product_id']}")

            product_reason = None
            if quarantine:
                product_reason = st.text_area(
                    f"Reason for Quarantining Product #{p['product_id']}",
                    max_chars=255,
                    value=quarantine_all_reason if quarantine_all else "",
                    key=f"quar_reason_{p['product_id']}"
                ).strip()

            visual = None
            if failed_sample:
                default_vis = sample_visual_results.get(p["product_id"], True)
                visual = st.radio(
                    "Visual Pass", 
                    [True, False], 
                    index=0 if default_vis else 1, 
                    horizontal=True, 
                    key=f"full_vis_{p['product_id']}"
                )
            
            prior_result = p["current_status"]
            treat_required = p["surface_treat"]
            visual_val = visual if visual is not None else True

            qc_result = determine_qc_result(prior_result, treat_required, surface, sterilized, quarantine, visual_val)
            color = COLOR_MAP.get(qc_result, "black")

            st.markdown(f"**Suggested QC Result:** <span style='color:{color}; font-weight:bold'>{qc_result}</span>", unsafe_allow_html=True)
            full_qc.append({
                "product_id": p["product_id"],
                "surface_treat": surface,
                "sterilize": sterilized,
                "visual_pass": visual_val,
                "qc_result": qc_result,
                "quarantine_reason": product_reason
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