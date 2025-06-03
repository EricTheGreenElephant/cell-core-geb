import streamlit as st
import time
from db.orm_session import get_session
from services.production_services import get_harvested_products, update_harvest_fields
from services.filament_service import get_mounted_filaments
from services.lid_services import get_available_lid_batches


def render_harvest_edit_form():
    st.subheader("Edit Harvested Product Records")

    with get_session() as db:
        harvested = get_harvested_products(db)

    if not harvested:
        st.info("No harvested products available for editing.")
        return
    
    options = {
        f"#{h['harvest_id']} - {h['product_type']} by {h['printed_by']} on {h['print_date']}": h
        for h in harvested
    }

    selected_label = st.selectbox("Select Harvest Record to Edit", list(options.keys()))
    selected = options[selected_label]

    with get_session() as db:
        mount_options = get_mounted_filaments(db)
        lid_options = get_available_lid_batches(db)

    printer_map = {
        f"{m['serial_number']} on {m['printer_name']}": m["mount_id"]
        for m in mount_options
    }
    lid_map = {f"{l['serial_number']}": l["id"] for l in lid_options}

    new_mount = st.selectbox(
        "Assign New Filament Mount",
        options=list(printer_map.keys()),
        index=0
    )
    new_lid = st.selectbox(
        "Assign New Lid Batch",
        options=list(lid_map.keys()),
        index=0
    )

    reason = st.text_area("Reason for Edit", max_chars=255)
    if st.button("Update Harvest Record"):
        if not reason.strip():
            st.warning("A reason is required.")
            return
        
        updates = {}
        if selected["mount_id"] != printer_map[new_mount]:
            updates["filament_mounting_id"] = (selected["mount_id"], printer_map[new_mount])
        if selected["lid_id"] != lid_map[new_lid]:
            updates["lid_id"] = (selected["lid_id"], lid_map[new_lid])
        
        if not updates:
            st.info("No changes detected.")
            return

        try:
            with get_session() as db:
                update_harvest_fields(
                    db=db,
                    harvest_id=selected["harvest_id"],
                    updates=updates,
                    reason=reason,
                    user_id=st.session_state["user_id"]
                )
            st.success("Harvest record updated.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to update harvest record.")
            st.exception(e)