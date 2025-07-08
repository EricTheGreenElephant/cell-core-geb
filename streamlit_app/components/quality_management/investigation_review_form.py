import streamlit as st
from services.quality_management_services import get_investigated_products
from db.orm_session import get_session


def render_investigation_review():
    st.subheader("Products Under Investigation")

    try:
        with get_session() as db:
            products = get_investigated_products(db)

        if not products:
            st.info("No products are currently under investigation.")
            return
        
        for prod in products:
            with st.expander(f"Product #{prod.product_id} - {prod.product_type}"):
                st.write(f"**Stage:** {prod.current_stage_name}")
                st.write(f"**Last Updated:** {prod.last_updated_at.date()}")
                st.write(f"**Location:** {prod.location_name or 'N/A'}")
                st.write(f"**Initial QC Result:** {prod.inspection_result or 'N/A'}")
                st.write(f"**Deviation #:** {prod.deviation_number or 'N/A'}")
                st.write(f"**Comment:** {prod.comment or 'N/A'}")
                st.write(f"**Created By:** {prod.created_by}")
                st.write(f"**Created At:** {prod.created_at}")
    
    except Exception as e:
        st.error("Failed to load investigation records.")
        st.exception(e)