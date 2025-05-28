import time
import streamlit as st
from services.filament_service import update_filament_fields, get_storage_locations, get_filaments
from services.user_services import get_users
from db.orm_session import get_session
from datetime import datetime


def render_edit_filament_tab():
    st.markdown("### Edit Filament Info")

    with get_session() as db:
        filaments = get_filaments(db)
        locations = get_storage_locations(db)
        users = get_users(db)

    if not filaments:
        st.info("No filaments found.")
        return
    
    filament_options = {f"{f.serial_number} (ID {f.id})": f for f in filaments}
    selection = st.selectbox("Select Filament to Edit", list(filament_options.keys()))
    filament = filament_options[selection]

    location_labels = {f"{loc.location_name} - {loc.description or ''}": loc.id for loc in locations}
    location_names = list(location_labels.keys())
    current_loc_label = next((label for label, id in location_labels.items() if id == filament.location_id), None)

    user_labels = {f"{u.display_name} (ID {u.id})": u.id for u in users}
    user_names = list(user_labels.keys())
    current_user_label = next((label for label, id in user_labels.items() if id == filament.received_by), None)

    with st.form("edit_filament_form"):
        new_serial = st.text_input("Serial Number", value=filament.serial_number)
        new_weight = st.number_input("Weight (g)", min_value=0.0, value=filament.weight_grams, format="%.2f")
        new_location_label = st.selectbox("Storage Location", location_names, index=location_names.index(current_loc_label))
        new_qc_result = st.selectbox("QC Result", ["PASS", "FAIL"], index=0 if filament.qc_result == "PASS" else 1)
        new_user_label = st.selectbox("Received By", user_names, index=user_names.index(current_user_label))
        new_received_at = st.date_input("Received At", value=filament.received_at.date())
        reason  = st.text_area("Reason for Change", max_chars=255)

        submitted = st.form_submit_button("Submit Changes")

        if submitted:
            if not reason.strip():
                st.warning("A reason for the change is required.")
                return
            
            updates = {}
            if filament.serial_number != new_serial:
                updates["serial_number"] = (filament.serial_number, new_serial)
            if filament.weight_grams != new_weight:
                updates["weight_grams"] = (filament.weight_grams, new_weight)
            new_location_id = location_labels[new_location_label]
            if filament.location_id != new_location_id:
                updates["location_id"] = (filament.location_id, new_location_id)
            if filament.qc_result != new_qc_result:
                updates["qc_result"] = (filament.qc_result, new_qc_result)
            new_user_id = user_labels[new_user_label]
            if filament.received_by != new_user_id:
                updates["received_by"] = (filament.received_by, new_user_id)
            new_received_at_full = datetime.combine(new_received_at, datetime.min.time())
            if filament.received_at.date() != new_received_at:
                updates["received_at"] = (filament.received_at, new_received_at_full)
            
            if not updates:
                st.info("No changes detected.")
                return
            
            try:
                with get_session() as db:
                    update_filament_fields(
                        db=db,
                        filament_id=filament.id,
                        updates=updates,
                        reason=reason,
                        user_id=st.session_state["user_id"]
                    )
                st.success("Filament updated successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Update field.")
                st.exception(e)