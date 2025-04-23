import streamlit as st
from data.qc import get_printed_products, insert_product_qc


def render_qc_form():
    st.subheader("Quality Control - Printed Products")

    printed = get_printed_products()
    if not printed:
        st.info("No printed products waiting for QC.")
        return
    
    product_map = {
        f"#{p['harvest_id']} - {p['product_type']} (Lot: {p['lot_number']})": p
        for p in printed
    }

    selection = st.selectbox("Select Product for QC", list(product_map.keys()))
    selected = product_map[selection]

    avg_weight = selected["average_weight"]
    tolerance = selected["percentage_change"]
    weight_low = avg_weight * (1 - tolerance)
    weight_high = avg_weight * (1 + tolerance)

    st.markdown(f"**Target Weight:** {avg_weight:.2f}g ± {tolerance*100:.1f}%")
    st.markdown(f"**Accepted Range:** {weight_low:.2f}g to {weight_high:.2f}g")

    weight = st.number_input("Measured Weight (g)", min_value=0.0, format="%.2f")
    pressure = st.number_input("Pressure Drop (mbar)", min_value=0.0, format="%.2f")
    visual = st.radio("Visual Check", ["Pass", "Fail"])

    # Validation messages
    suggested_result = "Passed"
    if weight > 0:
        if weight < weight_low or weight > weight_high:
            st.error("Weight outside acceptable range.")
            suggested_result = "B-Ware"
    if visual == "Fail":
        suggested_result = "B-Ware"
    if pressure >= 6:
        suggested_result = "Waste"

    st.markdown(f"**Suggested Result:** `{suggested_result}`")
    with st.form("qc_form"):       
        # Manual override with default set to suggestion
        result = st.selectbox("Overall QC Result", ["Passed", "B-Ware", "Waste"])
        notes = st.text_area("Notes (optional)", max_chars=255)

        submitted = st.form_submit_button("Submit QC")

        if submitted:
            if weight == 0.0 or pressure == 0.0:
                st.warning("Please enter a valid weight and pressure before submitting.")
            elif suggested_result != result:
                st.warning("The suggested result and entered result do not match. Please check.")
            else:
                try:
                    user_id = st.session_state.get("user_id")
                    insert_product_qc(
                        harvest_id=selected["harvest_id"],
                        inspected_by=user_id,
                        weight_grams=weight,
                        pressure_drop=pressure,
                        visual_pass=(visual == "Pass"),
                        inspection_result=result,
                        notes=notes
                    )
                    st.success("QC submitted successfully.")
                except Exception as e:
                    st.error("Failed to submit QC.")
                    st.exception(e)
