import streamlit as st
import time
from services.filament_service import (
    get_acclimatized_filaments,
    get_available_printers,
    insert_filament_mount
)
from db.orm_session import get_session
from schemas.printer_schemas import PrinterOut


def render_mount_form():
    """
    Creates form that allows user to select filament to mount to printer.

    - Select filaments available from filament_acclimatization table
    - Selects printers that are currently active and not in use.
    - On submission, filament and printer are added to filament_mounting table
        creating new id. 
    """
    st.subheader("Mount Acclimatized Filament")

    with get_session() as db:
        filaments = get_acclimatized_filaments(db)
        printers: list[PrinterOut] = get_available_printers(db)

    if not filaments:
        st.info("No filaments have completed acclimatization.")
        return
    
    filament_options = {
        f"#{f['filament_id']} | {f['serial_number']} ({f['weight_grams']}g)": (f["id"], f["acclimatization_id"])
        for f in filaments
    }

    printer_options = {p.name: p.id for p in printers}

    if not printer_options:
        st.info("No available printers. All printers are currently in use.")
        return

    with st.form("mount_filament_form"):
        selected_filament = st.selectbox("Select Filament", list(filament_options.keys()))
        selected_printer = st.selectbox("Select Printer", list(printer_options.keys()))

        submitted = st.form_submit_button("Mount Filament")

        if submitted:
            try: 
                user_id = st.session_state.get("user_id")
                filament_id, acclimatization_id = filament_options[selected_filament]
                printer_id = printer_options[selected_printer]
                with get_session() as db:
                    insert_filament_mount(db, filament_id, printer_id, user_id, acclimatization_id)
                st.success("Filament mounted successfully!")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to mount filament.")
                st.exception(e)