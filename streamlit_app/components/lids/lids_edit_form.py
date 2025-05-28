import streamlit as st
import time
from services.lid_services import get_all_lids, update_lid_fields
from services.filament_service import get_storage_locations
from db.orm_session import get_session


def render_edit_lid_form():
    st.markdown("### Edit Existing Lids")

    with get_session() as db:
        lids = get_all_lids(db)
        locations = get_storage_locations(db)

    if not lids:
        st.info("No lids available.")
        return
    
    lid_map = {f"{l.serial_number} (ID {l.id})": l for l in lids}
    selection = st.selectbox("Select Lid", list(lid_map.keys()))
    lid = lid_map[selection]

    location_map = {f"{loc.location_type}: {loc.location_name} --- {loc.description or ''}": loc.id for loc in locations}
    current_location_label = next((label for label, id in location_map.items() if id == lid.location_id), None)

    with st.form("edit_lid_form"):
        new_serial = st.text_input("Serial Number", value=lid.serial_number)
        new_qc_result = st.selectbox("QC Result", ["PASS", "FAIL"], index=0 if lid.qc_result == "PASS" else 1)
        new_location_label = st.selectbox("Storage Location", list(location_map.keys()), index=list(location_map.keys()).index(current_location_label))
        reason = st.text_area("Reason for Change", max_chars=255)

        submitted = st.form_submit_button("Submit Changes")

        if submitted:
            if not reason.strip():
                st.warning("A reason for the change is required.")
                return
            
            updates = {}
            if lid.serial_number != new_serial:
                updates["serial_number"] = (lid.serial_number, new_serial)
            if lid.qc_result != new_qc_result:
                updates["qc_result"] = (lid.qc_result, new_qc_result)
                
            new_location_id = location_map[new_location_label]
            if lid.location_id != new_location_id:
                updates["location_id"] = (lid.location_id, new_location_id)
            
            if not updates:
                st.info("No changes detected.")
                return
            
            try:
                with get_session() as db:
                    update_lid_fields(
                        db=db,
                        lid_id=lid.id,
                        updates=updates,
                        reason=reason,
                        user_id=st.session_state["user_id"]
                    )
                st.success("Lid updated successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to update lid.")
                st.exception(e)