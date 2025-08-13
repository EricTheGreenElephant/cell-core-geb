import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.label.label_form import render_label_form


st.title("Label Generator")

# --- User Logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
try:
    require_access("Logistics", minimum_level="Write")
except:
    require_access("Production", minimum_level="Write")

# --- Render Label UI ---
render_label_form()

