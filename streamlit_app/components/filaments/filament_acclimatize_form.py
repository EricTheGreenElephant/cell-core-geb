import streamlit as st
import time
from services.filament_service import get_filaments_not_acclimatizing, insert_filament_acclimatization
from db.orm_session import get_session


def render_acclimatizing_form():
    st.markdown("Move Filament to Acclimatization")

    try:
        with get_session() as db:
            options = get_filaments_not_acclimatizing(db)
        if not options:
            st.info("All filaments are already acclimatizing or in production.")
        else:
            option_labels = {
                f"{f['serial_number']}": f["id"]
                for f in options
            }
            selected = st.selectbox("Select filament to move", list(option_labels.keys()))
            if st.button("Move to Acclimatization"):
                try:
                    with get_session() as db:
                        insert_filament_acclimatization(db, option_labels[selected], st.session_state["user_id"])
                    st.success("Filament moved to acclimatization.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Error moving filament.")
                    st.exception(e)
    except Exception as e:
        st.error("Could not load filament options.")
        st.exception(e)