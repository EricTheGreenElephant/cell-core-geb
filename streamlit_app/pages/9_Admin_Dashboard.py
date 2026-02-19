import streamlit as st
from utils.session import require_login, require_access
from utils.auth_ui import render_account_box
# from utils.auth import show_user_sidebar
from components.admin.reason_management import render_reason_management
from components.admin.print_specs_form import render_print_specs_admin
from components.admin.sku_create_form import render_sku_create_form
from components.admin.sku_update_form import render_sku_update_form
from components.logistics.storage_audit import render_shelf_stage_mismatch_report
from components.common.admin_record_lookup import render_admin_record_lookup
from components.common.toggle import toggle_button
from db.orm_session import get_session


st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("Admin Dashboard")

# Show user info and logout
# show_user_sidebar()
render_account_box(expanded=True, home_after_logout="/")

# --- Access Control ---
require_login()
access_level = require_access("Admin", minimum_level="Admin")

toggle = st.selectbox(
    label="Choose Option",
    options=[
        "Select an option...", 
        "Manage Issue Labels",
        "Update Product Print Specs",
        "Create Product SKU",
        "Update Product SKU"
    ],
    index=0,
)
if toggle == "Manage Issue Labels":
    render_reason_management()

if toggle == "Update Product Print Specs":
    render_print_specs_admin()

if toggle == "Create Product SKU":
    render_sku_create_form()

if toggle == "Update Product SKU":
    render_sku_update_form()