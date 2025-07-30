import streamlit as st
import time
from services.lid_services import get_all_lids, update_lid_fields
from services.seal_services import get_all_seals, update_seal_fields
from services.filament_service import get_storage_locations
from db.orm_session import get_session


def render_edit_lid_form(mode):
    st.markdown("### Edit Existing Lids")

    with get_session() as db:
        if mode == "Lid":
            inventory = get_all_lids(db)
        elif mode == "Seal":
            inventory = get_all_seals(db)

        locations = get_storage_locations(db)

    if not inventory:
        st.info(f"No {mode} Inventory Available.")
        st.stop()
    
    inventory_map = {f"{inv.serial_number} (ID {inv.id})": inv for inv in inventory}
    selection = st.selectbox("Select Lid", list(inventory_map.keys()))
    inventory_item = inventory_map[selection]

    location_map = {f"{loc.location_type}: {loc.location_name} --- {loc.description or ''}": loc.id for loc in locations}
    current_location_label = next((label for label, id in location_map.items() if id == inventory_item.location_id), None)

    with st.form("edit_lid_seal_form"):
        new_serial = st.text_input("Serial Number", value=inventory_item.serial_number)
        new_quantity = st.number_input("Quantity", value=inventory_item.quantity, min_value=1, step=1)
        new_qc_result = st.selectbox("QC Result", ["PASS", "FAIL"], index=0 if inventory_item.qc_result == "PASS" else 1)
        new_location_label = st.selectbox("Storage Location", list(location_map.keys()), index=list(location_map.keys()).index(current_location_label))
        reason = st.text_area("Reason for Change", max_chars=255)

        submitted = st.form_submit_button("Submit Changes")

        if submitted:
            if not reason.strip():
                st.warning("A reason for the change is required.")
                return
            
            updates = {}
            if inventory_item.serial_number != new_serial:
                updates["serial_number"] = (inventory_item.serial_number, new_serial)
            if inventory_item.qc_result != new_qc_result:
                updates["qc_result"] = (inventory_item.qc_result, new_qc_result)
            if inventory_item.quantity != new_quantity:
                updates["quantity"] = (inventory_item.quantity, new_quantity)
                
            new_location_id = location_map[new_location_label]
            if inventory_item.location_id != new_location_id:
                updates["location_id"] = (inventory_item.location_id, new_location_id)
            
            if not updates:
                st.info("No changes detected.")
                return
            
            try:
                user_id = st.session_state["user_id"]
                with get_session() as db:
                    if mode == "Lid":
                        update_lid_fields(
                            db=db,
                            lid_id=inventory_item.id,
                            updates=updates,
                            reason=reason,
                            user_id=user_id
                        )
                    if mode == "Seal":
                        update_seal_fields(
                            db=db,
                            seal_id=inventory_item.id,
                            updates=updates,
                            reason=reason,
                            user_id=user_id
                        )
                st.success(f"{mode} updated successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update {mode.lower()}s.")
                st.exception(e)