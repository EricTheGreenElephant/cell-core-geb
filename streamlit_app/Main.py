import streamlit as st
from utils.auth import show_user_sidebar
from components.common.login_widget import login_widget

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")
st.title("CellCore Production Tool")

# Show login if not logged in
login_widget()

name = st.session_state.get("display_name") or st.session_state.get("_principal_name")
email = st.session_state.get("_principal_upn")
if name or email:
    who = name or email or "User"
    if email and name:
        st.success(f"Welcome, {who} ({email})")
    else:
        st.success(f"Welcome, {who}")
        
    if "access" not in st.session_state:
        st.caption("You're signed in. Waiting for database/access to be available.")

# If user is logged in, show welcome message
if "user_id" in st.session_state:
    st.success(f"Welcome, {st.session_state.display_name}")
    st.markdown("Use the sidebar to navigate to an area of the application.")
    show_user_sidebar()
