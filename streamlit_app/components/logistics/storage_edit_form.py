
import streamlit as st
import time
from services.logistics_services import get_stored_products, update_tracking_storage
from services.filament_service import get_storage_locations
from db.orm_session import get_session

def render_storage_edit_form():
    st.subheader("Edit Storage Assignment")

    with get_session() as db:
        products = get_stored_products(db)
        locations = get_storage_locations(db)

    if not products:
        st.info("No products with storage assignments to edit.")
        return

    if not locations:
        st.warning("No storage locations found.")
        return

    location_map = {
        f"{loc.location_name} — {loc.description or ''}": loc.id
        for loc in locations
    }
    location_names = list(location_map.keys())

    product_map = {
        f"#{p['product_id']} —  Prod ID: {p['harvest_id']} - {p['product_type']} -- {p['current_status']}": p
        for p in products
    }

    selected_label = st.selectbox("Select Product to Edit", list(product_map.keys()))
    selected = product_map[selected_label]

    current_loc_label = next((label for label, id in location_map.items() if id == selected["location_id"]), None)
    new_location_label = st.selectbox("New Storage Location", location_names, index=location_names.index(current_loc_label))
    change_status = st.checkbox(label="Change Product Status", value=False, key=f"status_change_{selected["harvest_id"]}")
    if change_status:   
        new_status = st.selectbox(
            "New Product Status", 
            ["Moved to Quarantine", "Stored; Pending QM Approval for Treatment", "Stored; Pending QM Approval for Sales"], 
            index=0
        )
    else:
        new_status = selected["current_status"]

    reason = st.text_area("Reason for Edit", max_chars=255)

    if st.button("Submit Edit"):
        if not reason.strip():
            st.warning("Please provide a reason for the update.")
            return

        new_loc_id = location_map[new_location_label]
        updates = {}
        if selected["location_id"] != new_loc_id:
            updates["location_id"] = (selected["location_id"], new_loc_id)
        if selected["current_status"] != new_status:
            updates["current_status"] = (selected["current_status"], new_status)

        if not updates:
            st.info("No changes detected.")
            return

        try:
            with get_session() as db:
                update_tracking_storage(
                    db=db,
                    product_id=selected["product_id"],
                    updates=updates,
                    reason=reason,
                    user_id=st.session_state["user_id"]
                )
            st.success("Storage details updated successfully.")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error("Failed to update storage details.")
            st.exception(e)
