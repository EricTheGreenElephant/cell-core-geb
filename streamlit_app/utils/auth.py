# import streamlit as st
# from data.users import get_user_by_email, get_user_by_oid, upsert_user_by_oid
# from data.access import get_user_access, get_effective_access

# def _extract_identity(principal_json):
#     def _claims_list(p):
#         if isinstance(p, list) and p:
#             return p[0].get("user_claims", []) or p[0].get("claims", [])
#         if isinstance(p, dict):
#             return p.get("user_claims", []) or p.get("claims", [])
#         return []
    
#     clist = _claims_list(principal_json)

#     cmap = {}
#     for c in clist:
#         t = str(c.get("typ", "")).strip().lower()
#         if not t:
#             continue
#         cmap[t] = c.get("val")
    
#     def get_any(keys):
#         for k in keys:
#             v = cmap.get(k.lower())
#             if v:
#                 return v
#         return None 
    
#     oid = get_any(["oid", "http://schemas.microsoft.com/identity/claims/objectidentifier"])
#     upn = get_any([
#         "preferred_username",
#         "upn",
#         "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
#         "emails",
#     ])
#     display_name = get_any([
#         "name",
#         "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
#     ]) or (upn.split("@")[0] if upn else "User")

#     groups = [c.get("val") for c in clist
#               if str(c.get("typ", "")).strip().lower() in (
#                   "groups",
#                   "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
#               ) and c.get("val")]
#     return (oid, (upn or "").lower(), display_name, groups)
# # def _extract_identity(principal_json):
# #     """
# #     Parse the Azure App Service Easy Auth principal JSON
# #     and return (oid, upn, display_name, group_oids)
# #     """
# #     try: 
# #         ident = (principal_json or [{}])[0]
# #         claims = {c.get("typ"): c.get("val") for c in ident.get("user_claims", [])}

# #         oid = claims.get("oid")
# #         upn = (
# #             claims.get("preferred_username")
# #             or claims.get("upn")
# #             or claims.get("emails")
# #             or claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
# #         )
# #         display_name = claims.get("name") or (upn.split("@")[0] if upn else "User")

# #         group_oids = [c.get("val") for c in ident.get("user_claims", []) if c.get("typ") == "groups"]

# #         return oid, (upn or "").lower(), display_name, group_oids
# #     except Exception:
# #         return None, None, None, []
    
# def authenticate_principal(principal_json, mode="autoprovision"):
#     """
#     Authenticate a user based on Azure App Service Easy Auth principal.
#     - Extract OID, UPN, display name, and group OIDs.
#     - Upsert user into database.
#     - Build access rights (user + group).
#     """
#     oid, upn, display_name, group_oids = _extract_identity(principal_json)
#     if not oid:
#         return False, "Missing object ID (oid) in principal."
    
#     # Try to get existing user
#     user = get_user_by_oid(oid)
#     if not user:
#         if mode == "allowlist":
#             return False, "User not found or not authorized."
        
#         user_id, display_name = upsert_user_by_oid(
#             oid=oid, upn=upn, display_name=display_name
#         )
#     else:
#         user_id, display_name = user 

#         upsert_user_by_oid(oid=oid, upn=upn, display_name=display_name)

#     access = get_effective_access(user_id, group_oids)

#     st.session_state.user_id = user_id 
#     st.session_state.display_name = display_name
#     st.session_state.access = access
#     st.session_state["_auth_source"] = "entra"

#     return True, f"Welcome, {display_name}"
    
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
