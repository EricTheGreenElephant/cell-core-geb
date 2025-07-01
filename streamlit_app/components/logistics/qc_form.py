import streamlit as st
import time
from services.qc_services import get_printed_products, insert_product_qc
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
        f"#{p['product_id']} - {p['product_type']} (Lot: {p['lot_number']})": p
        for p in printed
    }

    selection = st.selectbox("Select Product for QC", list(product_map.keys()))
    selected = product_map[selection]

    avg_weight = selected["average_weight"]
    tolerance = selected["buffer_weight"]
    weight_low = avg_weight - tolerance
    weight_high = avg_weight + tolerance

    st.markdown(f"**Target Weight:** {avg_weight:.2f}g ± {tolerance}g")
    st.markdown(f"**Accepted Range:** {weight_low:.2f}g to {weight_high:.2f}g")

    weight = st.number_input("Measured Weight (g)", min_value=0.0, format="%.2f")
    pressure = st.number_input("Pressure Drop (mbar)", min_value=0.0, format="%.2f")
    visual = st.radio("Visual Check", ["Pass", "Fail"])

    # Conditional formatting for result
    color_map = {
        "Passed": "green",
        "B-Ware": "orange",
        "Quarantine": "blue",
        "Waste": "red"
    }

    # Validation messages
    result = "Passed"
    if weight > 0:
        if weight < weight_low or weight > weight_high:
            st.error("Weight outside acceptable range.")
            result = "B-Ware"
    if visual == "Fail":
        # Manual choice after visual inspection fail
        st.markdown("###### *** Visual inspection fail requires manual selection. ***")
        result = st.selectbox("Inspection Result:", ["B-Ware", "Quarantine"])
    if pressure >= 6:
        st.error("Pressure above the acceptable tolerance.")
        result = "Waste"

    # Set conditional color 
    color = color_map.get(result, "black")

    st.markdown(f"<p><strong>Final QC Result:</strong> <span style='color:{color}'>{result}</span></p>", unsafe_allow_html=True)
    
    with st.form("qc_form"):       
        notes = st.text_area("Notes (optional)", max_chars=255)

        submitted = st.form_submit_button("Submit QC")

        if submitted:
            if weight == 0.0 or pressure == 0.0:
                st.warning("Please enter a valid weight and pressure before submitting.")
            else:
                try:
                    user_id = st.session_state.get("user_id")
                    payload = ProductQCInput(
                        product_id=selected["product_id"],
                        inspected_by=user_id,
                        weight_grams=weight,
                        pressure_drop=pressure,
                        visual_pass=(visual == "Pass"),
                        inspection_result=result,
                        notes=notes
                    )
                    with get_session() as db:
                        insert_product_qc(db=db, data=payload)
                    st.success("QC submitted successfully.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Failed to submit QC.")
                    st.exception(e)
