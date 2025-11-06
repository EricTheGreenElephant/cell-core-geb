import streamlit as st
import json
from utils.auth import show_user_sidebar
from components.common.login_widget import login_widget

st.set_page_config(page_title="CellCore Production Dashboard", layout="wide")
st.title("CellCore Production")

try:
    # Lazy import so this file stays independent
    from components.common.login_widget import _fetch_principal_via_auth_me
    from utils.auth import _extract_identity
    principal = _fetch_principal_via_auth_me()
    with st.expander("Debug • Raw /.auth/me (remove after testing)"):
        st.code(json.dumps(principal, indent=2) if principal else "No principal")

    if principal:
        oid, upn, display_name, groups = _extract_identity(principal)
        st.write("**Parsed from claims:**")
        st.json({
            "display_name": display_name,
            "upn": upn,
            "oid": oid,
            "groups_count": len(groups)
        })
except Exception as e:
    st.warning(f"Principal debug failed: {e}")

# Show login if not logged in
login_widget()

# Prefer DB-authenticated name, fall back to claims-based name
name = st.session_state.get("display_name") or st.session_state.get("_principal_name")
email = st.session_state.get("_principal_upn")

if name or email:
    who = name or email or "User"
    st.success(f"Welcome, {who}" + (f" ({email})" if email and email != who else ""))
    if "access" not in st.session_state:
        st.caption("Signed in with Microsoft Entra. App features appear once database/access is loaded.")
else:
    st.info("Please sign in to continue.")
# name = st.session_state.get("display_name") or st.session_state.get("_principal_name")
# email = st.session_state.get("_principal_upn")
# if name or email:
#     who = name or email or "User"
#     if email and name:
#         st.success(f"Welcome, {who} ({email})")
#     else:
#         st.success(f"Welcome, {who}")

#     if "access" not in st.session_state:
#         st.caption("You're signed in. Waiting for database/access to be available.")

# If user is logged in, show welcome message
if "user_id" in st.session_state:
    st.success(f"Welcome, {st.session_state.display_name}")
    st.markdown("Use the sidebar to navigate to an area of the application.")
    show_user_sidebar()
