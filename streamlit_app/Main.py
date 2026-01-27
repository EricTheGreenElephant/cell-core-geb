import streamlit as st
from utils.auth import get_current_user
from utils.auth_ui import render_account_box
from utils.access_bootstrap import ensure_user_and_access

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")

render_account_box(expanded=True, home_after_logout="/")

user = get_current_user()

if not user:
    st.title("Unauthorized")
    st.write("You must be logged in to use application.")
    st.stop()

#Uncomment after testing
user_id, access_map = ensure_user_and_access()

# 5️ App content (only runs if signed in)
st.title("CellCore Development")
st.write(f"Welcome, **{user['name'] or user['email'] or 'friend'}**!")

# show who/what (comment out in prod)
# with st.expander("Debug: identity & access", expanded=False):
#     st.write({"user_id": user_id, "access": access_map, "group_oids": st.session_state.get("group_oids")})

# Example: simple authorization gate by Entra Object ID (best practice)
# ALLOWED_OIDS = {""}  # replace with real OIDs
# if user["oid"] not in ALLOWED_OIDS:
#     st.error("You don’t have access to this page.")
#     st.stop()

st.success("You are authorized 🎉")

# Uncomment for database connection tests

from utils.db import run_query

st.header("Database Connection Test")

if st.button("Test Database Connection"):
    try:
        run_query("SELECT TOP (5) name, create_date FROM sys.tables ORDER BY create_date DESC;")
        # st.success("✅ Connected successfully using Managed Identity!")
        # st.write("Here are some tables SQL sees:")
        # st.table(rows)
    except Exception as e:
        st.error(f"❌ Database connection failed:\n\n{e}")

