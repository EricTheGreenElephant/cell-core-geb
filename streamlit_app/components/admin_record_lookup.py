import streamlit as st
# from data.admin_tools import get_product_record, update_product_field
from data.admin_tools import (
    get_all_filaments,
    get_all_product_ids,
    get_all_lids,
    get_record_by_id,
    update_record_with_audit
)


def render_admin_record_lookup():
    st.subheader("Admin Record Lookup & Edit")

    table_choice = st.selectbox("Select Table", ["Filaments", "Products", "Lids"])

    # --- Step 1: Load records for selected table ---
    record_map = {}
    if table_choice == "Filaments":
        filaments = get_all_filaments()
        record_map = {f"{f['serial_number']}": f["id"] for f in filaments}
    elif table_choice == "Products":
        products = get_all_product_ids()
        record_map = {f"Product #{p['id']}": p["id"] for p in products}
    elif table_choice == "Lids":
        lids = get_all_lids()
        record_map = {f"{l['serial_number']}": l["id"] for l in lids}

    if not record_map:
        st.warning("No records found.")
        return
    
    # --- Step 2: Record selection ---
    selected_label = st.selectbox("Select Record", list(record_map.keys()))
    selected_id = record_map[selected_label]

    # --- Step 3: Fetch and display record ---
    try:
        record = get_record_by_id(table_choice, selected_id)
        if not record:
            st.warning("No record found.")
            return
        
        st.markdown("### Edit Record")
        changes = {}
        with st.form("edit_record_form"):
            for key, value in record.items():
                if key in ["id", "created_at", "received_at"]:
                    st.text_input(key, value, disabled=True)
                else:
                    new_value = st.text_input(key, str(value))
                    if str(value) != new_value:
                        changes[key] = new_value
            
            submitted = st.form_submit_button("Save Changes")
            if submitted and changes:
                update_record_with_audit(table_choice, selected_id, changes, st.session_state.get("user_id"))
                st.success("Record updated and changes logged.")
                st.rerun()

    except Exception as e:
        st.error("Failed to load or update record.")
        st.exception(e)


    # tracking_id = st.text_input("Enter Tracking ID", placeholder="e.g., 1054")

    # if tracking_id:
    #     try:
    #         record = get_product_record(tracking_id)
    #         if not record:
    #             st.warning("No record found with that tracking ID.")
    #             return
            
    #         st.json(record)

    #         st.markdown("### Update Field")
    #         field_to_edit = st.selectbox("Select field to update", list(record.keys()))
    #         new_value = st.text_input(f"Enter new value for '{field_to_edit}'")

    #         if st.button("Update Record"):
    #             user_id = st.session_state.get("user_id")
    #             success = update_product_field(tracking_id, field_to_edit, new_value, user_id)
    #             if success:
    #                 st.success("Record updated successfully.")
    #                 st.rerun()
    #             else:
    #                 st.error("Failed to update record. Check logs or permissions.")
    #     except Exception as e:
    #         st.error("Something went wrong.")
    #         st.exception(e)