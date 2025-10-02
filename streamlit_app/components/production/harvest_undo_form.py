import streamlit as st
import time
from services.production_services import get_harvested_products, undo_product_harvest
from db.orm_session import get_session


def render_harvest_undo_form():
    st.markdown("### Undo Harvested Product")

    with get_session() as db:
        harvested = get_harvested_products(db)

    if not harvested:
        st.info("No harvested products available for undo.")
        return
    
    product_labels = {
        f"#{p['harvest_id']} - {p['sku']} - {p['sku_name']} - Printed on {p['print_date']}": p
        for p in harvested
    }

    selected_label = st.selectbox("Select Harvest to Undo", list(product_labels.keys()))
    selected = product_labels[selected_label]

    with st.form("undo_harvest_form"):
        reason = st.text_area("Reason for undoing harvest", max_chars=255)
        confirm = st.checkbox("Confirm you want to undo this harvest")
        submitted = st.form_submit_button("Undo Harvest")

        if submitted:
            if not confirm:
                st.warning("You must confirm the undo action.")
                return
            if not reason.strip():
                st.warning("Reason for change is required.")
                return

            try:
                with get_session() as db:
                    undo_product_harvest(
                        db=db,
                        harvest_id=selected["harvest_id"],
                        reason=reason.strip(),
                        user_id=st.session_state["user_id"]
                    )
                st.success("Harvest successfully undone.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error("Failed to undo harvest.")
                st.exception(e)