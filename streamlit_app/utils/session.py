import streamlit as st
from utils.access_bootstrap import ensure_user_and_access

def require_login():
    ensure_user_and_access()
    # if "user_id" not in st.session_state:
    #     st.warning("Please log in to access this page.")
    #     st.stop()

def require_access(area, minimum_level="Read"):
    ensure_user_and_access()
    access = st.session_state.get("access", [])
    user_level = access.get(area)

    if not user_level:
        st.error(f"You do not have access to '{area}'")
        st.stop()

    hierarchy = ["Read", "Write", "Admin"]
    if hierarchy.index(user_level) < hierarchy.index(minimum_level):
        st.error(f"{minimum_level} access required for this action.")
        st.stop()

    return user_level
