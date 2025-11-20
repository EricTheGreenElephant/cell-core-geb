import streamlit as st
from services.filament_service import search_filament
from db.orm_session import get_session


def render_filament_weight_update():
    filament_id = st.number_input(
        label="Enter Filament ID:",
        placeholder="e.g. 101",
        step=1
    )
    with get_session() as db:
        filament = search_filament(db, filament_id)

    if filament:
        st.write(filament)
    else:
        st.warning("Filament ID not found! Please enter valid ID.")
        return