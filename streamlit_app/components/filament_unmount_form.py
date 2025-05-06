import streamlit as st
from data.filament import get_mounted_filaments, unmount_filament

def render_unmount_form():
    st.markdown("Unmount Filament")

    try:
        mounted = get_mounted_filaments()

        if not mounted:
            st.info("No currently mounted filaments.")
        else:
            mount_labels = {
                f"{m['serial_number']} on {m['printer_name']} ({m['remaining_weight']}g left)": m["mount_id"]
                for m in mounted
            }
            selected = st.selectbox("Select filament to unmount", list(mount_labels.keys()))
            if st.button("Unmount Selected"):
                try:
                    user_id = st.session_state.get("user_id")
                    unmount_filament(mount_labels[selected], user_id)
                    st.success("Filament unmounted successfully.")
                    st.rerun()
                except Exception as e:
                    st.error("Failed to unmount filament.")
                    st.exception(e)
    except Exception as e:
        st.error("Could not load mounted filaments.")
        st.exception(e)