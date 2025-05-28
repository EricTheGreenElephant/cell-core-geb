import streamlit as st
import time
from db.orm_session import get_session
from services.filament_service import restore_acclimatizing_filaments, delete_filament_acclimatization


def render_restore_acclimatization_form():
    st.markdown("### Restore Acclimatization")

    try: 
        with get_session() as db:
            acclimatized = restore_acclimatizing_filaments(db)

        if not acclimatized:
            st.info("No filaments currently in acclimatization that can be restored.")
            return
        
        option_labels = {
            f"{f['serial_number']} (Ready: {f['ready_at'].date()}, Location: {f['location_name']})": f['acclimatization_id']
            for f in acclimatized
        }

        selection = st.selectbox("Select filament to restore", list(option_labels.keys()))
        reason = st.text_area("Reason for restoration", max_chars=255)

        if st.button("Restore Acclimatization"):
            if not reason.strip():
                st.warning("Please provide a reason for the change.")
                return
            
            acclimatization_id = option_labels[selection]
            user_id = st.session_state.get("user_id")

            try:
                with get_session() as db:
                    delete_filament_acclimatization(
                        db=db,
                        acclimatization_id=acclimatization_id,
                        reason=reason,
                        user_id=user_id
                    )
                st.success("Acclimatization restored successfully.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to restore acclimatization.")
                st.exception(e)

    except Exception as e:
        st.error("Could not load acclimatized filaments.")
        st.exception(e)