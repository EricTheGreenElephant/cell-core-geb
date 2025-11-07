# import streamlit as st
# from data.users import get_user_by_email, get_user_by_oid, upsert_user_by_oid
# from data.access import get_user_access, get_effective_access

    
# def authenticate_user(email: str):
#     user = get_user_by_email(email.strip().lower())

#     if not user:
#         return False, "User not found or not authorized"
    
#     user_id = user[0]
#     display_name = user[1]

#     st.session_state.user_id = user_id
#     st.session_state.display_name = display_name
#     st.session_state.access = get_user_access(user_id)

#     return True, f"Welcome, {display_name}"

# def show_user_sidebar():
#     if "user_id" in st.session_state:
#         with st.sidebar:
#             st.markdown(f"**{st.session_state.display_name}**")

#             if st.button("Logout", type="primary"):
#                 st.session_state.clear()
#                 st.switch_page("Main.py")
#                 st.rerun()


# auth.py
import base64, json
import streamlit as st

def _get_request_headers():
    """
    Get the original HTTP request headers in a Streamlit app
    (works on Azure App Service with Entra ID / EasyAuth).
    """
    try:
        # Preferred modern API (Streamlit 1.39+)
        return st.context.headers or {}
    except Exception:
        # Fallback for older Streamlit versions
        try:
            from streamlit.script_run_context import get_script_run_ctx  # type: ignore
            from streamlit.server.server import Server  # type: ignore
            ctx = get_script_run_ctx()
            if not ctx:
                return {}
            session_info = Server.get_current()._get_session_info(ctx.session_id)
            return getattr(session_info.ws.request, "headers", {}) or {}
        except Exception:
            return {}

def _parse_client_principal(principal_b64: str):
    data = json.loads(base64.b64decode(principal_b64))
    claims = {c["typ"]: c["val"] for c in data.get("claims", [])}

    def first(*keys):
        for k in keys:
            if claims.get(k):
                return claims[k]
        return None

    return {
        "name": first(
            "name",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        ),
        "email": first(
            "preferred_username",
            "emails",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        ),
        "oid": first(
            "oid",
            "http://schemas.microsoft.com/identity/claims/objectidentifier",
        ),
        "tid": first("tid", "http://schemas.microsoft.com/identity/claims/tenantid"),
        "roles": [
            c["val"]
            for c in data.get("claims", [])
            if c["typ"].endswith("/role") or c["typ"] == "roles"
        ],
        "raw": data,
    }

def get_current_user():
    """
    Returns dict(name, email, oid, tid, roles, raw) or None if not signed in.
    """
    headers = {k.lower(): v for k, v in _get_request_headers().items()}
    principal_b64 = headers.get("x-ms-client-principal")
    if principal_b64:
        try:
            return _parse_client_principal(principal_b64)
        except Exception:
            pass

    # Simpler header fallback
    name = headers.get("x-ms-client-principal-name")
    oid = headers.get("x-ms-client-principal-id")
    tid = headers.get("x-ms-client-principal-tenant-id")
    if name or oid:
        return {"name": name, "email": name, "oid": oid, "tid": tid, "roles": [], "raw": {}}

    return None
