import streamlit as st
from data.filament import get_acclimatized_filaments, get_available_printers, insert_filament_mount

def render_mount_form():
    st.subheader("Mount Acclimatized Filament")

    filaments = get_acclimatized_filaments()
    printers = get_available_printers()

    if not filaments:
        st.info("No filaments have completed acclimatization.")
        return
    
    filament_options = {
        f"{f['serial_number']} ({f['material_type']}, {f['weight_grams']}g)": (f["id"], f["acclimatization_id"])
        for f in filaments
    }

    printer_options = {p[1]: p[0] for p in printers}

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
                insert_filament_mount(filament_id, printer_id, user_id, acclimatization_id)
                st.success("Filament mounted successfully!")
            except Exception as e:
                st.error("Failed to mount filament.")
                st.exception(e)