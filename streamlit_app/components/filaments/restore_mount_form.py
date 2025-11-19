import time 
import streamlit as st
from db.orm_session import get_session
from services.filament_mount_services import update_mount_fields, get_unmounted_mounts


def render_restore_mount_form():
    """
    Creates form that allows user to re-mount unmounted filament.

    - Fetches filaments with unmounted status
    - On submission,
        - Edits filament_mounting table
        - Inserts record into audit_log table
    """
    st.subheader("Restore Unmounted Filament")

    with get_session() as db:
        mounts = get_unmounted_mounts(db)

    if not mounts:
        st.info("No unmounted filaments available for restoration.")
        return
    
    options = {
        f"#{m['filament_id']} | {m['serial_number']} on {m['printer_name']} (Unmounted at {m['unmounted_at']} - Remaining Weight: {m['remaining_weight']})": m for m in mounts
    }

    selection = st.selectbox("Select Unmounted Filament to Restore", list(options.keys()))
    selected = options[selection]

    reason = st.text_area("Reason for restoration", max_chars=255).strip()

    if st.button("Restore Filament"):
        if not reason:
            st.warning("A reason is required.")
            return
        
        updates = {}
        if selected["unmounted_at"] is not None:
            updates["unmounted_at"] = (selected["unmounted_at"], None)
        if selected.get("unmounted_by") is not None:
            updates["unmounted_by"] = (selected["unmounted_by"], None)
        if selected["status"] != "In Use":
            updates["status"] = (selected["status"], "In Use")
        
        if not updates:
            st.info("No fields need restoring.")
            return

        try:
            with get_session() as db:
                update_mount_fields(
                    db=db,
                    mount_id=selected["mount_id"],
                    updates=updates,
                    reason=reason,
                    user_id=st.session_state["user_id"]
                )
            st.success("Filament restored successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to restore filament.")
            st.exception(e)