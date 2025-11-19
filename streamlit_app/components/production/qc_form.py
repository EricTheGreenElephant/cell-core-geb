import streamlit as st
import time
from constants.general_constants import COLOR_MAP
from services.qc_services import get_printed_products, insert_product_qc
from services.reasons_services import get_reasons_for_context, filter_reasons_by_outcome
from schemas.qc_schemas import ProductQCInput
from db.orm_session import get_session


def render_qc_form():
    st.subheader("Quality Control - Printed Products")

    with get_session() as db:
        printed = get_printed_products(db)
    if not printed:
        st.info("No printed products waiting for QC.")
        return
    
    product_map = {
        f"#{p['product_id']} | {p['printer']} | {p['sku']} - {p['sku_name']}": p
        for p in printed
    }

    selection = st.selectbox("Select Product for QC", list(product_map.keys()))
    selected = product_map[selection]

    with get_session() as db:
        reason_rows = get_reasons_for_context(db, "HarvestQC")

    avg_weight = float(selected["average_weight_g"] or 0)
    tolerance = float(selected["weight_buffer_g"] or 0)
    weight_low = avg_weight - tolerance
    weight_high = avg_weight + tolerance

    st.markdown(f"**Target Weight:** {avg_weight:.2f}g ± {tolerance}g")
    st.markdown(f"**Accepted Range:** {weight_low:.2f}g to {weight_high:.2f}g")

    weight = st.number_input("Measured Weight (g)", min_value=0, key=f"hqc_weight_{selected['product_id']}")

    st.markdown("**Pressure Testing parameters:**")
    st.markdown("* 500 mbar ± 100 mbar")
    st.markdown("* 6 mbar tolerance")
    st.markdown("* 30 second measurement time")

    pressure = st.number_input("Pressure Drop (mbar)", min_value=0.0, format="%.2f", key=f"hqc_pressure_{selected['product_id']}")
    visual = st.radio("Visual Check", ["Pass", "Fail"], key=f"hqc_visual_{selected['product_id']}")

    # Validation messages
    result = "Passed"
    if weight > 0:
        if weight < weight_low or weight > weight_high:
            st.error("Weight outside acceptable range.")
            result = "B-Ware"

    if pressure >= 6:
        st.error("Pressure above the acceptable tolerance.")
        result = "Waste"

    chosen_reason_ids: list[int] = []
    notes_placholder = ""

    if visual == "Fail" and result != "Waste":
        st.markdown("##### *** Visual inspection fail requires manual selection. ***")

        result = st.selectbox("Inspection Result:", ["B-Ware", "Quarantine"], key=f"hqc_visfail_result_{selected['product_id']}")
        filtered_reasons = filter_reasons_by_outcome(reason_rows, result)
        reason_options = {f"{r['reason_label']} [{r['category']}]": r["id"] for r in filtered_reasons}

        chosen_reason_labels = st.multiselect(
            "Reason(s) for failure",
            options=list(reason_options.keys()),
            key=f"hqc_visfail_reasons_{selected['product_id']}"
        )
        chosen_reason_ids = [reason_options[label] for label in chosen_reason_labels]
        notes_placholder = "; ".join(chosen_reason_labels)

    # Set conditional color 
    color = COLOR_MAP.get(result, "black")

    st.markdown(f"<p><strong>Final QC Result:</strong> <span style='color:{color}'>{result}</span></p>", unsafe_allow_html=True)
    if result == "B-Ware":
        st.info("Please don't forget to indicate B-Ware on the label!")
    elif result == "Waste":
        st.info("Please don't forget to indicate Waste on the label!")
    
    with st.form("qc_form"):       
        notes = st.text_area("Notes (optional)", value=notes_placholder, max_chars=255, key=f"hqc_notes_{selected['product_id']}").strip()

        submitted = st.form_submit_button("Submit QC")

        if submitted:
            if weight == 0.0 or pressure == 0.0:
                st.warning("Please enter a valid weight and pressure before submitting.")
            else:
                if visual == "Fail" and result == "B-Ware" and not notes.strip():
                    st.error("Notes are required when selecting B-Ware due to a Visual Fail.")
                    return
                try:
                    user_id = st.session_state.get("user_id")
                    payload = ProductQCInput(
                        product_tracking_id=selected["id"],
                        inspected_by=user_id,
                        weight_grams=weight,
                        pressure_drop=pressure,
                        visual_pass=(visual == "Pass"),
                        inspection_result=result,
                        notes=notes,
                        reason_ids=chosen_reason_ids
                    )
                    with get_session() as db:
                        insert_product_qc(db=db, data=payload)
                    st.success("QC submitted successfully.")
                    for key in list(st.session_state.keys()):
                        if key.startswith("hqc_"):
                            del st.session_state[key]
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Failed to submit QC.")
                    st.exception(e)
