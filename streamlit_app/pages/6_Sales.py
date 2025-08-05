import streamlit as st
from utils.session import require_login, require_access
from utils.auth import show_user_sidebar
from components.sales.sales_inventory_form import render_sales_tab
from components.sales.sales_order_form import render_sales_order_form
from components.common.toggle import toggle_button


st.title("Sales")

# --- User logout ---
show_user_sidebar()

# --- Login Check ---
require_login()
require_access("Sales", minimum_level="Write")

toggle = st.selectbox(
    label="Choose Option",
    options=["Select an option...", "View Sales Inventory", "Create Sales Order"],
    index=0,
)
if toggle == "View Sales Inventory":
    render_sales_tab()

elif toggle == "Create Sales Order":
    render_sales_order_form()