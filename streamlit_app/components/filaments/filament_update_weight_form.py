import streamlit as st
import time
from services.filament_service import search_filament, update_filament_weight
from db.orm_session import get_session


def render_filament_weight_update():
    filament_id = st.number_input(
        label="Enter Filament ID:",
        placeholder="e.g. 101",
        step=1,
        format="%d",
    )

    if st.button("Search Filament"):
        with get_session() as db:
            filament = search_filament(db, filament_id)

        if not filament:
            st.warning("Filament ID not found! Please enter a valid ID.")
            return

        # Display info
        st.info(
            f"Filament ID: {filament['filament_id']} | "
            f"Serial: {filament['serial_number']} | "
            f"Current weight: {filament['current_weight']} g "
            f"(source: {filament['weight_source']})"
        )

        # Make sure we have some default numeric value
        current_weight = filament["current_weight"] or 0.0
        with st.form("update_weight_form"):
            updated_weight = st.number_input(
                label="Enter updated weight (g):",
                value=float(current_weight),
                min_value=0.0,
                format="%0.2f",
            )
            submitted = st.form_submit_button("Save updated weight")
            if submitted:
                with get_session() as db:
                    update_filament_weight(
                        db,
                        filament_pk=filament["filament_pk"],
                        new_weight=updated_weight,
                        table_updated=filament["weight_source"]
                    )
                st.success("Filament weight updated successfully.")
                time.sleep(1)
                st.rerun()
