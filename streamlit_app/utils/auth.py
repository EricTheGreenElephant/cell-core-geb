import base64, json, os, secrets
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

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

def _get_user_from_easy_auth():
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

def _env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key, default)
    return v

def _is_local() -> bool:
    return (_env("APP_ENV", "prod") or "prod").lower() in ("local", "dev")

def _query_params() -> dict:
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()
    
def _clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()

def _build_msal_app():
    import msal
    client_id = _env("AZURE_CLIENT_ID")
    tenant_id = _env("AZURE_TENANT_ID")
    client_secret = _env("AZURE_CLIENT_SECRET")

    if not client_id or not tenant_id or not client_secret:
        raise RuntimeError("Missing AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE CLIENT SERVICE for local auth.")
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    cache = st.session_state.get("_msal_cache")
    if cache is None:
        cache = msal.SerializableTokenCache()
        st.session_state["_msal_cache"] = cache 

    return msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret,
        token_cache=cache,
    )

def _scopes():
    return ["User.Read", "GroupMember.Read.All"]

def _user_from_id_token_claims(claims: dict) -> dict:
    email = claims.get("preferred_username") or claims.get("email")
    name = claims.get("name") or email
    oid = claims.get("oid") or claims.get("http://schemas.microsoft.com/identity/claims/objectidentifier")
    tid = claims.get("tid") or claims.get("http://schemas.microsoft.com/identity/claims/tenantid")
    roles = claims.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    return {"name": name, "email": email, "oid": oid, "tid": tid, "roles": roles, "raw": claims}

def _handle_local_redirect():
    """
    If Entra redirected back with ?code=..., exchange it for tokens and set st.session_state["user"].
    """
    params = _query_params()
    code = None

    if "code" in params:
        code_val = params["code"]
        code = code_val[0] if isinstance(code_val, list) else code_val

    if not code:
        return 

    app = _build_msal_app()
    redirect_uri = _env("AZURE_REDIRECT_URI", "http://localhost:8501")
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=_scopes(),
        redirect_uri=redirect_uri
    )

    _clear_query_params()

    if "id_token_claims" not in result:
        st.error(f"Authentication failed. Details: {result.get('error_description') or result.get('error')}")
        st.stop()
    
    st.session_state["user"] = _user_from_id_token_claims(result["id_token_claims"])

    if result.get("access_token"):
        st.session_state["graph_access_token"] = result.get("access_token")

def _local_login_ui():
    """
    Show a sign-in link and stop execution.
    """
    app = _build_msal_app()
    redirect_uri = _env("AZURE_REDIRECT_URI", "http://localhost:8501")

    if "_auth_state" not in st.session_state:
        st.session_state["_auth_state"] = secrets.token_urlsafe(16)

    auth_url = app.get_authorization_request_url(
        scopes=_scopes(),
        redirect_uri=redirect_uri,
        state=st.session_state["_auth_state"],
        prompt="select_account",
    )

    st.markdown("### Sign in")
    st.markdown(f"[Sign in with Microsoft]({auth_url})")
    st.stop()

def get_current_user():
    """
    Unified entry point:
    - In Azure (prod): read EasyAuth headers (x-ms-client-principal)
    - Locally: use MSAL and session_state
    """
    user = _get_user_from_easy_auth()
    if user:
        return user
    
    if _is_local():
        _handle_local_redirect()

        if "user" in st.session_state:
            return st.session_state["user"]

        _local_login_ui()
    
    return None