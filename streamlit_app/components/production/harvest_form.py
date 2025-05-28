import streamlit as st
import time
from services.production_services import (
    get_pending_requests,
    insert_product_harvest,
    cancel_product_request
)
from services.lid_services import get_available_lid_batches
from services.filament_service import get_mountable_filament_mounts
from db.orm_session import get_session

def render_harvest_form():
    st.subheader("Fulfill Product Request")

    with get_session() as db:
        pending = get_pending_requests(db)

    if not pending:
        st.info("No pending product requests")
        return

    for unit in pending:
        with st.expander(f"🧾 Request #{unit['id']} – {unit['product_type']} (Lot: {unit['lot_number']})"):
            st.markdown(f"**Requested by:** {unit['requested_by']}  \n**Date:** {unit['requested_at']}")

            # Calculate required weight with tolerated buffer weight and additional buffer  
            avg = unit["average_weight"]
            buffer = unit["buffer_weight"]
            required_weight = avg + buffer + 10
            
            # Filter available printers based on weight
            with get_session() as db:
                mounts = get_mountable_filament_mounts(db, required_weight)

            if not mounts:
                st.info("No active mounted printers have enough filament available to fulfill this request.")
                continue 
            
            mount_options = {
                        f"{m['serial_number']} on {m['printer_name']} ({m['remaining_weight']}g left)": m['id']
                        for m in mounts
            }

            with st.form(f"form_unit_{unit['id']}"):
                selected_mount = st.selectbox("Assign Printer with Filament", list(mount_options.keys()), key=f"mount_{unit['id']}")
                
                with get_session() as db:
                    lid_batches = get_available_lid_batches(db)

                if lid_batches:
                    lid_options = {f"{l['serial_number']}": l["id"] for l in lid_batches}
                    selected_lid = st.selectbox("Select Lid Batch", options=list(lid_options.keys()), key=f"lid_{unit['id']}")
                    lid_id = lid_options[selected_lid]
                else:
                    st.warning("No passing lid batches available.")
                    lid_id = None
                cols = st.columns([1, 1])
                with cols[0]:
                    submitted = st.form_submit_button("✅ Harvest Product")
                with cols[1]:
                    cancel = st.form_submit_button("❌ Cancel Product")

                if submitted:
                    try:
                        mount_id = mount_options[selected_mount]
                        user_id = st.session_state.get("user_id")
                        with get_session() as db:
                            insert_product_harvest(
                                db,
                                request_id=unit['id'], 
                                filament_mount_id=mount_id, 
                                printed_by=user_id, 
                                lid_id=lid_id
                            )
                        st.success("Product marked as harvested.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error("Error fulfilling request.")
                        st.exception(e)
                elif cancel:
                    try:
                        with get_session() as db:
                            cancel_product_request(db, unit['id'])
                        st.warning("Product request has been cancelled.")
                    except Exception as e:
                        st.error("Failed to cancel.")
                        st.exception(e)