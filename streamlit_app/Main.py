import streamlit as st
from utils.auth import show_user_sidebar
from components.login_widget import login_widget

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")
st.title("CellCore")

# Show login if not logged in
login_widget()

# If user is logged in, show welcome message
if "user_id" in st.session_state:
    st.success(f"Welcome, {st.session_state.display_name}")
    st.markdown("Use the sidebar to navigate to an area of the application.")
    show_user_sidebar()
