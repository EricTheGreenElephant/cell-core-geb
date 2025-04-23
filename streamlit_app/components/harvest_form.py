import streamlit as st
from data.production import get_pending_requests, get_mountable_filament_mounts, insert_product_harvest, cancel_product_request


def render_harvest_form():
    st.subheader("Fulfill Product Request")

    pending = get_pending_requests()

    if not pending:
        st.info("No pending product requests")
        return

    for unit in pending:
        with st.expander(f"🧾 Request #{unit['id']} – {unit['product_type']} (Lot: {unit['lot_number']})"):
            st.markdown(f"**Requested by:** {unit['requested_by']}  \n**Date:** {unit['requested_at']}")

            # Calculate required weight with buffer
            avg = unit["average_weight"]
            pct = unit["percentage_change"]
            required_weight = avg * (1 + pct) + 10
            
            # Filter available printers based on weight
            mounts = get_mountable_filament_mounts(required_weight)
            if not mounts:
                st.info("No active mounted printers have enough filament available to fulfill this request.")
                continue 
            
            mount_options = {
                        f"{m['serial_number']} on {m['printer_name']} ({m['remaining_weight']}g left)": m['id']
                        for m in mounts
            }

            with st.form(f"form_unit_{unit['id']}"):
                selected_mount = st.selectbox("Assign Printer with Filament", list(mount_options.keys()), key=f"mount_{unit['id']}")
                cols = st.columns([1, 1])
                with cols[0]:
                    submitted = st.form_submit_button("✅ Harvest Product")
                with cols[1]:
                    cancel = st.form_submit_button("❌ Cancel Product")

                if submitted:
                    try:
                        mount_id = mount_options[selected_mount]
                        user_id = st.session_state.get("user_id")
                        insert_product_harvest(request_id=unit['id'], filament_mount_id=mount_id, printed_by=user_id)
                        st.success("Product marked as harvested.")
                    except Exception as e:
                        st.error("Error fulfilling request.")
                        st.exception(e)
                elif cancel:
                    try:
                        cancel_product_request(unit['id'])
                        st.warning("Product request has been cancelled.")
                    except Exception as e:
                        st.error("Failed to cancel.")
                        st.exception(e)