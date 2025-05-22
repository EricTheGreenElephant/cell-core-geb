import time
import streamlit as st
from services.filament_service import get_storage_locations
from data.lids import insert_lid
from db.orm_session import get_session


def render_add_lid_form():
    st.markdown("### Add New Lid Batch")

    with st.form("add_lid_batch_form"):
        serial_number = st.text_input("Serial Number")

        # Fetch storage location options
        with get_session() as db:
            locations = get_storage_locations(db)
        location_dict = {
            # Label that appears in dropdown with key selection
            f"{loc['location_type']}: {loc['location_name']} --- Description: {loc['description']}": loc['id'] 
            for loc in locations
            }
        location_name = st.selectbox("Storage Location", list(location_dict.keys()))

        qc_result = st.selectbox("QC Result", ["PASS", "FAIL"])

        submitted = st.form_submit_button("Add Batch")

        if submitted:
            try:
                if not serial_number.strip():
                    st.warning("Serial number is required.")
                    return

                insert_lid(
                    serial_number=serial_number.strip(),
                    location_id=location_dict[location_name],
                    qc_result=qc_result,
                    received_by=st.session_state.get("user_id")
                )
                st.success("Lid batch successfully added.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to add lid batch.")
                st.exception(e)