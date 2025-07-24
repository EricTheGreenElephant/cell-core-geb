import streamlit as st
from data.users import get_user_by_email
from data.access import get_user_access

def authenticate_user(email: str):
    user = get_user_by_email(email.strip().lower())

    if not user:
        return False, "User not found or not authorized"
    
    user_id = user[0]
    display_name = user[1]

    st.session_state.user_id = user_id
    st.session_state.display_name = display_name
    st.session_state.access = get_user_access(user_id)

    return True, f"Welcome, {display_name}"

def show_user_sidebar():
    if "user_id" in st.session_state:
        with st.sidebar:
            st.markdown(f"**{st.session_state.display_name}**")

            if st.button("Logout", type="primary"):
                st.session_state.clear()
                st.switch_page("Main.py")
                st.rerun()