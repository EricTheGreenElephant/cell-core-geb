import streamlit as st
from services.filament_service import get_all_filament_statuses
from db.orm_session import get_session


def render_health_status():
    """
    Renders a view of the currrently mounted filaments. 
    
    - Indicates the weight and criticality of filament.
    """
    st.subheader("Filament Health Status")

    try:
        # Creates database session and calls service function to get all filaments
        with get_session() as db:
            all_filaments = get_all_filament_statuses(db)

        # Filters for filaments currently in use    
        in_use = [f for f in all_filaments if f["current_status"] == "In Use"]

        if not in_use:
            st.info("No filaments currently in use.")
        else:
            for filament in in_use:
                remaining = filament.get("remaining_weight")
                label = f"**{filament['serial_number']}** on {filament['printer_name']}"

                # Displays remaining weights and levels of criticality
                if remaining is not None:
                    if remaining < 500:
                        st.error(f"{label} - **Critical** - Replace Now ({remaining}g left)")
                    elif remaining < 2500:
                        st.warning(f"{label} - **Low** - Prepare Replacement ({remaining}g left)")
                    else:
                        st.success(f"{label} - **OK** - ({remaining}g left)")
                else:
                    st.info(f"{label} - Spool not currently mounted")
    except Exception as e:
        st.error("Failed to load filament health status.")
        st.exception(e)