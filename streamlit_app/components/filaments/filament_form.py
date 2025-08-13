import streamlit as st
import time
from schemas.filament_schemas import FilamentCreate
from services.filament_service import insert_filament, get_storage_locations
from schemas.storage_location_schemas import StorageLocationOut
from db.orm_session import get_session

def render_add_filament_form():
    """
    Displays a Streamlit form that allows users to input a new filament into database.

    - Fetches storage locations from database
    - Allows user to input filament information
    - On submission, adds the new filament to the database
    """
    st.subheader("Add New Filament")

    # Get user info
    user_id = st.session_state.get("user_id")
    user_name = st.session_state.get("display_name")

    # Get storage locations
    with get_session() as db:
        locations: list[StorageLocationOut] = get_storage_locations(db)

    # Format to display storage location options
    location_options = {
        f"{loc.location_name} --- (Type: {loc.location_type}) (Desc.: {loc.description})": loc.id 
        for loc in locations
        }

    # Check for user login
    if not user_id:
        st.error("User must be logged in to add filaments.")
        return
    
    st.info(f"Received by: **{user_name}**")

    # Creates the form display with inputs
    with st.form("add_filament_form"):
        lot_number = st.text_input("Lot Number", max_chars=100).strip()
        serial_number = st.text_input("Serial Number", max_chars=100).strip()
        weight_grams = st.number_input("Initial Weight (g)", min_value=0.0, format="%.2f")
        location_label = st.selectbox("Storage Location", list(location_options.keys()))
        qc_result = st.selectbox("QC Result", ["PASS", "FAIL"])

        submitted = st.form_submit_button("Add Filament")

        if submitted:
            if not lot_number:
                st.warning("Please enter a valid lot number.")
                return

            if not serial_number:
                st.warning("Please enter a valid serial number.")
                return
            
            if weight_grams <= 0:
                st.warning("Please enter a valid weight.")
                return

            try:
                location_id = location_options[location_label]   

                # Packages filament data             
                filament_data = FilamentCreate(
                    lot_number=lot_number,
                    serial_number=serial_number,
                    weight_grams=weight_grams,
                    location_id=location_id,
                    qc_result=qc_result,
                    received_by=user_id
                )

                # Create database session and calls function to handle query
                with get_session() as db:
                    insert_filament(db, filament_data)
                st.success(f"Filament spool '{serial_number}' added successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to add filament.")
                st.exception(e)