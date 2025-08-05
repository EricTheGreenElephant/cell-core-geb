import streamlit as st
import time
from services.expiration_services import get_expiring_products, expire_eligible_products
from db.orm_session import get_session


def render_expiration_review():
    st.subheader("Expiration Management")

    with get_session() as db:
        soon, expired = get_expiring_products(db)

    if not soon and not expired:
        st.success("No products nearing expiration.")
        st.stop()
    
    if soon:
        st.markdown("### Expiring Soon (Within 7 Days)")
        st.dataframe(soon, use_container_width=True)

    if expired:
        st.markdown("### Already Expired (Over 1 Year Old)")
        st.dataframe(expired, use_container_width=True)

        if st.button("Updated Expired Products", use_container_width=True, type="primary"):
            with get_session() as db:
                user_id = st.session_state.get("user_id")
                if not user_id:
                    st.error("You must be logged in to perform this action.")
                    st.stop()
                updated = expire_eligible_products(db, user_id)
                st.success(f"{updated} products marked as expired.")
                time.sleep(1.5)
                st.rerun()