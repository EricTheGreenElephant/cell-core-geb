import streamlit as st
import time
from services.filament_service import search_filament, update_filament_weight
from db.orm_session import get_session


SESSION_KEY = "filament_weight_search_result"


def render_filament_weight_update():
    st.subheader("Update Filament Weight")

    with st.form("filament_weight_search"):
        filament_id_input = st.text_input(
            "Filament ID",
            value="",
            help="Type the filament ID (from filaments.filament_id)."
        )
        search_submitted = st.form_submit_button("Search")


    if search_submitted:
        if not filament_id_input.strip():
            st.warning("Please enter a filament ID before searching.")
        else:
            try:
                filament_id = int(filament_id_input)
            except ValueError:
                st.error("Filament ID must be a number.")
            else:
                with get_session() as db:
                    result = search_filament(db, filament_id)
                
                if result is None:
                    st.error(f"No filament found with ID {filament_id}.")
                    st.session_state.pop(SESSION_KEY, None)
                else:
                    st.session_state[SESSION_KEY] = result
    
    result = st.session_state.get(SESSION_KEY)
    if not result:
        return

    st.markdown("---")
    st.write("### Current Filament")

    weight_source_label = {
        "mounting": "Mounted (filament_mounting.remaining_weight)",
        "filament": "In storage (filaments.weight_grams)",
        "none": "No weight recorded",
    }.get(result["weight_source"], result["weight_source"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Filament ID", str(result["filament_id"]))
    col2.metric("Serial Number", result["serial_number"])
    col3.metric(
        "Current weight (g)",
        (
            f"{result['current_weight']:.2f}"
            if result["current_weight"] is not None
            else "-"
        ),
    )

    st.caption(f"Weight Source: **{weight_source_label}**")

    if result["current_weight"] is None:
        st.info(
            "There is no current weight recorded for this filament."
            "You can set an initial value below."
        )

    with st.form("filament_weight_update"):
        new_weight = st.number_input(
            "New weight (g)",
            min_value=0.0,
            value=float(result["current_weight"] or 0.0),
            step=0.1,
            format="%.2f",
        )
        submitted = st.form_submit_button("Update Weight")
    
    if submitted:
        with get_session() as db:
            update_filament_weight(
                db=db,
                filament_pk=result["filament_pk"],
                new_weight=float(new_weight),
                table_updated=result["weight_source"],
            )

            refreshed = search_filament(db, result["filament_id"])
        
        if refreshed is not None:
            st.session_state[SESSION_KEY] = refreshed
        st.success("Filament weight updated successfully.")

    filament_id = st.number_input(
        label="Enter Filament ID:",
        placeholder="e.g. 101",
        step=1,
        format="%d",
    )

    # if st.button("Search Filament"):
    #     with get_session() as db:
    #         filament = search_filament(db, filament_id)

    #     if not filament:
    #         st.warning("Filament ID not found! Please enter a valid ID.")
    #         return

    #     # Display info
    #     st.info(
    #         f"Filament ID: {filament['filament_id']} | "
    #         f"Serial: {filament['serial_number']} | "
    #         f"Current weight: {filament['current_weight']} g "
    #         f"(source: {filament['weight_source']})"
    #     )

    #     # Make sure we have some default numeric value
    #     current_weight = filament["current_weight"] or 0.0
    #     with st.form("update_weight_form"):
    #         updated_weight = st.number_input(
    #             label="Enter updated weight (g):",
    #             value=float(current_weight),
    #             min_value=0.0,
    #             format="%0.2f",
    #         )

    #         submitted = st.form_submit_button("Save updated weight")
    #         if submitted:
    #             if updated_weight != filament["current_weight"]:
    #                 new_weight = updated_weight
    #             else:
    #                 st.info("No updates detected!")
    #                 return
    #             try:
    #                 with get_session() as db:
    #                     update_filament_weight(
    #                         db,
    #                         filament_pk=filament["filament_pk"],
    #                         new_weight=new_weight,
    #                         table_updated=filament["weight_source"]
    #                     )
    #                 st.success("Filament weight updated successfully.")
    #                 time.sleep(1.5)
    #                 st.rerun()
    #             except Exception as e:
    #                 st.error("Update Failed")
    #                 st.exception(e)