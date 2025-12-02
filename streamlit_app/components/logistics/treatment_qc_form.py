import time 
import streamlit as st
from random import sample
from services.logistics_services import (
    get_shipped_batches,
    get_products_by_batch_id,
    update_post_treatment_qc,
    mark_batch_as_inspected
)
from services.reasons_services import get_reasons_for_context, filter_reasons_by_outcome
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
            reason_rows = get_reasons_for_context(db, "PostTreatmentQC")

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

        # Sets the random sample to prevent re-randomizing product selection when user changes visual pass option
        sample_key = f"sample_batch_{batch_id}"
        if sample_key not in st.session_state:
            st.session_state[sample_key] = sample(products, actual_sample_size)
        random_sample = st.session_state[sample_key]

        failed_sample = False
        sample_visual_results = {}
        if not override_all:
            st.markdown(f"**Randomly Selected for Visual Inspection: {sample_size} of {total} products**")
            for i, p in enumerate(random_sample):
                inspection_result = "B-Ware" if p["current_status"] == "B-Ware" else "A-Ware"
                st.markdown(f"**Sample #{i+1}: Product #{p['product_id']} - {p['sku']} - {p['sku_name']}: {inspection_result}**")
                p["visual_pass"] = st.radio(
                    f"Visual Pass (Product #{p['product_id']})", [True, False], horizontal=True, key=f"vis_{p['product_id']}"
                )
                sample_visual_results[p["product_id"]] = p["visual_pass"]
                if not p['visual_pass']:
                    failed_sample = True
        else:
            st.info("Override enabled: 100% visual inspection required for this batch.")

        st.divider()
        st.markdown("### Full Inspection")

        # === Quarantine All (adds shared reasons/notes) ===
        quarantine_all = st.checkbox("Quarantine All", value=False)
        qa_reason_labels= []
        quarantine_all_reason = ""

        if quarantine_all:
            st.info("All products will be forced to Quarantine.")
            q_filtered = filter_reasons_by_outcome(reason_rows, "Quarantine")
            q_reason_options = {f"{r['reason_label']} [{r['category']}]": r["id"] for r in q_filtered}

            qa_reason_labels = st.multiselect(
                "Reason(s) for Quarantine (applied to all products)",
                options=list(q_reason_options.keys()),
                key="quarantine_all_reason_codes"
            )

            quarantine_all_reason = st.text_area(
                "Quarantine Notes (applied to all products)",
                value="; ".join(qa_reason_labels),
                max_chars=255,
                key="quarantine_all_reason_text"
            ).strip()

        # === Per-product Section ===
        full_qc = []
        for p in products:
            inspection_result = "B-Ware" if p["current_status"] == "B-Ware" else "A-Ware"
            st.markdown(f"**Product #{p['product_id']} - {p['sku']} - {p['sku_name']}: {inspection_result}**")

            surface = st.checkbox("Surface Treated", value=p["surface_treat"], key=f"surf_{p['product_id']}")
            sterilized = st.checkbox("Sterilized", value=p["sterilize"], key=f"ster_{p['product_id']}")

            quarantine = st.checkbox("Quarantine", value=quarantine_all, key=f"quar_{p['product_id']}")

            chosen_reason_ids = []
            chosen_reason_labels = []
            chosen_notes = ""

            if quarantine:
                # Forced outcome: Quarantine; hide visual radios
                q_filtered = filter_reasons_by_outcome(reason_rows, "Quarantine")
                q_opts = {f"{r['reason_label']} [{r['category']}]": r["id"] for r in q_filtered}

                chosen_reason_labels = st.multiselect(
                    f"Reason(s) for Quarantine (Product #{p['product_id']})",
                    options=list(q_opts.keys()),
                    default=qa_reason_labels if quarantine_all else None,
                    key=f"q_reasons_{p['product_id']}"
                )
                chosen_reason_ids = [q_opts[label] for label in chosen_reason_labels]

                chosen_notes = st.text_area(
                    f"Quarantine Notes for Product #{p['product_id']}",
                    value=(quarantine_all_reason if quarantine_all else "; ".join(chosen_reason_labels)),
                    max_chars=255,
                    key=f"q_notes_{p['product_id']}"
                ).strip()

                qc_result = "Quarantine"
                visual = None   
            else:
                visual = True
                if override_all or failed_sample:
                    default_vis = sample_visual_results.get(p["product_id"], True)
                    visual = st.radio(
                        "Visual Pass", 
                        [True, False], 
                        index=0 if default_vis else 1, 
                        horizontal=True, 
                        key=f"full_vis_{p['product_id']}"
                    )
                chosen_outcome = None

                if visual is False:
                    chosen_outcome = st.radio(
                        "Outcome for Visual FAIL",
                        ["Waste", "B-Ware", "Quarantine"],
                        index=0,
                        horizontal=True,
                        key=f"visfail_outcome_{p['product_id']}",
                        help="If choosing B-Ware/Quarantine, a note is required."
                    )

                    # if chosen_outcome != 'Waste':
                    if chosen_outcome:
                        filtered_reasons = filter_reasons_by_outcome(reason_rows, chosen_outcome)
                        reason_opts = {f"{r['reason_label']} [{r['category']}]": r["id"] for r in filtered_reasons}

                        chosen_reason_labels = st.multiselect(
                            "Reason(s) for failure",
                            options=list(reason_opts.keys()),
                            key=f"visfail_reasons_{p['product_id']}"
                        )
                        chosen_reason_ids = [reason_opts[label] for label in chosen_reason_labels]

                        suggested_text = "; ".join(chosen_reason_labels)
                        chosen_notes = st.text_area(
                            "Notes (required)",
                            value=suggested_text,
                            max_chars=255,
                            key=f"visfail_notes_{p['product_id']}"
                        ).strip()
                
                prior_result = p["current_status"]
                treat_required = p["surface_treat"]
                visual_val = visual if visual is not None else True

                suggested_qc = determine_qc_result(prior_result, treat_required, surface, sterilized, quarantine, visual_val)
                qc_result = chosen_outcome if (visual_val is False and chosen_outcome) else suggested_qc

            color = COLOR_MAP.get(qc_result, "black")
            st.markdown(f"**Suggested QC Result:** <span style='color:{color}; font-weight:bold'>{qc_result}</span>", unsafe_allow_html=True)

            full_qc.append({
                "product_id": p["id"],
                "surface_treat": surface,
                "sterilize": sterilized,
                "visual_pass": True if quarantine else (visual if visual is not None else True),
                "qc_result": qc_result,
                "quarantine_reason": chosen_notes if (quarantine or qc_result == "Quarantine") else None,
                "notes": chosen_notes,
                "reason_ids": chosen_reason_ids
            })

        if st.button("Finalize Inspection"):
            try:
                for item in full_qc:
                    if item.get("visual_pass") is False and item.get("qc_result") == "B-Ware":
                        if not item.get("notes" or "").strip():
                            st.error(f"Notes are required for Product #{item['product_id']} when selecting B-Ware on a visual fail.")
                            return
                    if item.get("qc_result") == "Quarantine" and not item.get("reason_ids"):
                        st.warning(f"Consider selecting at least one standardized reason for Product #{item['product_id']} (Quarantine)")

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