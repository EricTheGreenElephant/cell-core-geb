import streamlit as st
from services.quality_management_services import get_audit_log_entries
from db.orm_session import get_session


def render_audit_log_view():
    st.subheader("Audit Log")

    try:
        with get_session() as db:
            audit_entries = get_audit_log_entries(db)
    except Exception as e:
        st.error("Failed to load audit log.")
        st.exception(e)
        return
    
    if not audit_entries:
        st.info("No audit entries found.")
        return
    
    st.dataframe(audit_entries, use_container_width=True)
    