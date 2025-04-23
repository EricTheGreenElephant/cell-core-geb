import streamlit as st
from utils.session import require_access, require_login
from utils.auth import show_user_sidebar
from components.logistics_form import render_logistics_form


require_login()
require_access("Logistics", "Write")

show_user_sidebar()
st.title("Logistics & Treatment Dispatch")

render_logistics_form()