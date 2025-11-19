import time
import streamlit as st
from services.filament_mount_services import get_mounts_with_filaments, update_mount_fields
from services.user_services import get_users
from services.printer_services import get_printers
from db.orm_session import get_session
from datetime import datetime


def render_edit_mount_form():
    """
    Creates form that allows user to edit mounted filament

    - Fetches mounted filaments, users, and printers
    - Allows user to edit status
    - Allows user to edit information of record
    - On submission
        - Updates filament_mounting table with new data
        - Inserts record into audit_log
    """
    st.subheader("Edit Filament Mounting Info")

    with get_session() as db:
        mounts = get_mounts_with_filaments(db)
        users = get_users(db)
        printers = get_printers(db)

    if not mounts:
        st.info("No mounted filaments found.")
        return
    
    mount_options = {
        f"#{m.filament.filament_id} | {m.filament.serial_number} on {m.printer.name} (ID {m.id})": m for m in mounts
    }

    selection = st.selectbox("Select Mounting Record", list(mount_options.keys()))

    mount = mount_options[selection]

    user_labels = {f"{u.display_name} (ID {u.id})": u.id for u in users}
    user_names = list(user_labels.keys())
    current_user_label = next((label for label, id in user_labels.items() if id == mount.mounted_by), None)

    current_unmounted_by_label = None
    if mount.unmounted_by:
        current_unmounted_by_label = next(
            (label for label, id in user_labels.items() if id == mount.unmounted_by), 
            None
        ) 

    printer_labels = {f"{p.name} (ID {p.id})": p.id for p in printers}
    printer_names = list(printer_labels.keys())
    current_printer_label = next((label for label, id in printer_labels.items() if id == mount.printer_id), None)

    new_status = st.selectbox("Mounting Status", ["In Use", "Unmounted"], index=0 if mount.status == "In Use" else 1)

    with st.form("edit_mount_form"):
        if new_status == "In Use":
            new_weight = st.number_input("Remaining Weight (g)", min_value=0.0, value=mount.remaining_weight, format="%.2f")
            new_user_label = st.selectbox("Mounted By", user_names, index=user_names.index(current_user_label))
            new_mounted_at = st.date_input("Mounted At", value=mount.mounted_at.date())
            new_printer_label = st.selectbox("Printer", printer_names, index=printer_names.index(current_printer_label))

        if new_status == "Unmounted":
            new_unmounted_by_label = st.selectbox(
                "Unmounted By (if unmounting)", 
                user_names, 
                index=user_names.index(current_unmounted_by_label) if current_unmounted_by_label else 0
            )
            new_unmounted_by_id = user_labels[new_unmounted_by_label]

            new_unmounted_at = st.date_input(
                "Unmounted At (if unmounting)", 
                value=mount.unmounted_at.date() if mount.unmounted_at else datetime.today()
            )
            new_unmounted_at_full = datetime.combine(new_unmounted_at, datetime.min.time())
        else:
            new_unmounted_by_id = None
            new_unmounted_at_full = None

        reason = st.text_area("Reason for Change", max_chars=255).strip()

        submitted = st.form_submit_button("Submit Changes")

        if submitted:
            if not reason:
                st.warning("A reason for the change is required.")
                return
            
            updates = {}
            if mount.remaining_weight != new_weight:
                updates["remaining_weight"] = (mount.remaining_weight, new_weight)
            new_user_id = user_labels[new_user_label]
            if mount.mounted_by != new_user_id:
                updates["mounted_by"] = (mount.mounted_by, new_user_id)
            new_mounted_at_full = datetime.combine(new_mounted_at, datetime.min.time())
            if mount.mounted_at.date() != new_mounted_at:
                updates["mounted_at"] = (mount.mounted_at, new_mounted_at_full)
            if mount.status != new_status:
                updates["status"] = (mount.status, new_status)
            if mount.unmounted_by != new_unmounted_by_id:
                updates["unmounted_by"] = (mount.unmounted_by, new_unmounted_by_id)
            if (mount.unmounted_at or None) != new_unmounted_at_full:
                updates["unmounted_at"] = (mount.unmounted_at, new_unmounted_at_full)
            new_printer_id = printer_labels[new_printer_label]
            if mount.printer_id != new_printer_id:
                updates["printer_id"] = (mount.printer_id, new_printer_id)
            
            if not updates:
                st.info("No changes detected.")
                return
            
            try: 
                with get_session() as db:
                    update_mount_fields(
                        db=db,
                        mount_id=mount.id,
                        updates=updates,
                        reason=reason,
                        user_id=st.session_state["user_id"]
                    )
                st.success("Mounting record updated successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Update failed.")
                st.exception(e)