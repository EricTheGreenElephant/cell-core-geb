import streamlit as st
import time
from schemas.filament_schemas import FilamentCreate
from services.filament_service import insert_filament, get_storage_locations
from schemas.storage_location_schemas import StorageLocationOut
from db.orm_session import get_session

def render_add_filament_form():
    st.markdown("Add New Filament")

    # Get user info
    user_id = st.session_state.get("user_id")
    user_name = st.session_state.get("display_name")

    # Get storage locations
    with get_session() as db:
        locations: list[StorageLocationOut] = get_storage_locations(db)

    location_options = {
        f"{loc.location_name} --- (Type: {loc.location_type}) (Desc.: {loc.description})": loc.id 
        for loc in locations
        }

    if not user_id:
        st.error("User must be logged in to add filaments.")
        return
    
    st.info(f"Received by: **{user_name}**")


    with st.form("add_filament_form"):
        serial_number = st.text_input("Serial Number", max_chars=100)
        weight_grams = st.number_input("Initial Weight (g)", min_value=0.0, format="%.2f")
        location_label = st.selectbox("Storage Location", list(location_options.keys()))
        qc_result = st.selectbox("QC Result", ["PASS", "FAIL"])

        submitted = st.form_submit_button("Add Filament")

        if submitted:
            try:
                location_id = location_options[location_label]                
                filament_data = FilamentCreate(
                    serial_number=serial_number.strip(),
                    weight_grams=weight_grams,
                    location_id=location_id,
                    qc_result=qc_result,
                    received_by=user_id
                )
                with get_session() as db:
                    insert_filament(db, filament_data)
                st.success(f"Filament spool '{serial_number}' added successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to add filament.")
                st.exception(e)