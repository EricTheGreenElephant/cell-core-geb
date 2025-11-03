import os
import json
import base64
import streamlit as st
from utils.auth import authenticate_user


def _easy_auth_principal():
    """
    If running behind Azure App Service Easy Auth, return the principal dict.
    Otherwise return None. Safe to call locally.
    """
    raw = st.session_state.get("_X_MS_CLIENT_PRINCIPAL")
    if not raw:
        raw = os.environ.get("X_MS_CLIENT_PRINCIPAL")
    if not raw:
        return None
    try:
        data = json.loads(base64.b64decode(raw).decode("utf-8"))
        return data
    except Exception:
        return None 
    
def login_widget():
    """Reusable login form that only display if user is not logged in."""

    if "user_id" not in st.session_state:
        principal = _easy_auth_principal()
        if principal:
            email = None
            for claim in principal.get("claims", []):
                if claim.get("typ") in ("https://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                                        "emails",
                                        "name"):
                    email = claim.get("val")
                    break
            email = email or os.environ.get("X_MS_CLIENT_PRINCIPAL_NAME")
            if email:
                success, message = authenticate_user(email)
                if success:
                    st.session_state["_auth_source"] = "entra"
                    st.toast(f"Signed in as {email}")
                    return 
                
    if "user_id" in st.session_state:
        return 
    
    with st.form("login_form"):
        st.subheader("🔐 Please log in to continue")
        email = st.text_input("Email address", placeholder="you@company.com")

        submitted = st.form_submit_button("Login")
        if submitted and email:
            success, message = authenticate_user(email)
            if success:
                st.success(message)
                st.rerun()
            else: st.error(message)

            