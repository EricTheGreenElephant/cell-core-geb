import streamlit as st
from utils.session import require_login, require_access
from utils.auth_ui import render_account_box
# from utils.auth import show_user_sidebar
# from components.sales.sales_inventory_form import render_sales_tab
from components.sales.sales_order_form import render_sales_order_form
from components.sales.canceled_orders_form import render_canceled_orders_form
# from components.sales.update_order_form import render_update_order_form
from components.common.toggle import toggle_button


st.title("Sales")

# --- User logout ---
# show_user_sidebar()
render_account_box(expanded=True, home_after_logout="/")

# --- Login Check ---
require_login()
require_access("Sales", minimum_level="Write")

toggle = st.selectbox(
    label="Choose Option",
    options=[
        "Select an option...", 
        "View Sales Inventory", 
        "Create Sales Order",
        "Update or Cancel Order",
        "Re-submit Canceled Orders"
    ],
    index=0,
)
if toggle == "View Sales Inventory":
    # render_sales_tab()
    pass

elif toggle == "Create Sales Order":
    render_sales_order_form(mode="new")

elif toggle == "Update or Cancel Order":
    render_sales_order_form(mode="update")
    
elif toggle == "Re-submit Canceled Orders":
    render_canceled_orders_form()