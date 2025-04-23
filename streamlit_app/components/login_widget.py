import streamlit as st
from utils.auth import authenticate_user

def login_widget():
    """Reusable login form that only display if user is not logged in."""

    if "user_id" in st.session_state:
        return # Already loggin in, nothing to show
    
    with st.form("login_form"):
        st.subheader("🔐 Please log in to continue")
        email = st.text_input("Email address", placeholder="you@company.com")

        submitted = st.form_submit_button("Login")
        if submitted and email:
            success, message = authenticate_user(email)
            if success:
                st.success(message)
                st.rerun()
            else: st.error(message)

            