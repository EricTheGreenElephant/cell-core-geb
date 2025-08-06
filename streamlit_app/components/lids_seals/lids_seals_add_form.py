import time
import streamlit as st
from schemas.lid_schemas import LidCreate
from schemas.seals_schemas import SealCreate
from services.filament_service import get_storage_locations
from services.lid_services import insert_lids
from services.seal_services import insert_seals
from db.orm_session import get_session


def render_add_lid_seal_form(mode: str):
    """
    Creates form that allows user to add new batch of lids or seals

    Parameters
        - mode: str
            Passed parameter of either 'Lid' or 'Seal'

    - Fetches available storage locations
    - Creates form that allows user input
    - Inserts new record to seals or lids table based on selection (mode)
    """
    st.subheader(f"Add New {mode} Batch")

    # Fetch storage location options
    with get_session() as db:
        locations = get_storage_locations(db)
    location_dict = {
        # Label that appears in dropdown with key selection
        f"{loc.location_type}: {loc.location_name} --- Description: {loc.description}": loc.id
        for loc in locations
    }

    with st.form("add_lid_seal_batch_form"):
        serial_number = st.text_input("Serial Number").strip()
        quantity = st.number_input("Batch Quantity", min_value=1, step=1)
        location_name = st.selectbox("Storage Location", list(location_dict.keys()))
        qc_result = st.selectbox("QC Result", ["PASS", "FAIL"])

        submitted = st.form_submit_button("Add Batch")

        if submitted:
            try:
                if not serial_number:
                    st.warning("Serial number is required.")
                    return
                
                if mode == "Lid":
                    lid_data = LidCreate(
                        serial_number=serial_number,
                        quantity=quantity,
                        location_id=location_dict[location_name],
                        qc_result=qc_result,
                        received_by=st.session_state.get("user_id")
                    )

                    with get_session() as db:
                        insert_lids(db, lid_data)
                
                elif mode == "Seal":
                    seal_data = SealCreate(
                        serial_number=serial_number,
                        quantity=quantity,
                        location_id=location_dict[location_name],
                        qc_result=qc_result,
                        received_by=st.session_state.get("user_id")
                    )

                    with get_session() as db:
                        insert_seals(db, seal_data)

                st.success(f"{mode} batch successfully added.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add {mode.lower()} batch.")
                st.exception(e)