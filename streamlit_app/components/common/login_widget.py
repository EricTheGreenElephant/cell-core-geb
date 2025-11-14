# import os
# import json
# import base64
# import streamlit as st
# from streamlit_js_eval import streamlit_js_eval
# from utils.auth import authenticate_user, authenticate_principal, _extract_identity



# def _extract_email_from_principal(principal_dict):
#     if not principal_dict:
#         return None
    
#     # Easy Auth returns an array of identities. Takes the first.
#     ident = (principal_dict or [{}])[0]
#     claims = {c.get("typ"): c.get("val") for c in ident.get("user_claims", [])}

#     # Try common claim types in order:
#     for k in (
#         "preferred_username",
#         "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
#         "emails",
#         "upn",
#         "name"
#     ):
#         if claims.get(k):
#             return claims[k].strip().lower()
#     return None

# def _easy_auth_principal():
#     """
#     If running behind Azure App Service Easy Auth, return the principal dict.
#     Otherwise return None. Safe to call locally.
#     """
#     raw = st.session_state.get("_X_MS_CLIENT_PRINCIPAL")
#     if not raw:
#         raw = os.environ.get("X_MS_CLIENT_PRINCIPAL")
#     if not raw:
#         return None
#     try:
#         data = json.loads(base64.b64decode(raw).decode("utf-8"))
#         return data
#     except Exception:
#         return None 




# def  _server_principal(): 
#     """
#     Read Easy Auth principal from server env header
#     """
#     raw = os.environ.get("X_MS_CLIENT_PRINCIPAL")
#     st.write(raw)
#     if not raw:
#         return None
#     try:
#         return json.loads(base64.b64decode(raw).decode("utf-8"))
#     except Exception:
#         return None 
    
# def login_widget():
#     """Reusable login form that only display if user is not logged in."""

#     if "user_id" in st.session_state:
#         return
    
#     principal = _server_principal()

#     if principal:
#         try:
#             ok, msg = authenticate_principal(principal, mode="autoprovision")
#             if ok: 
#                 st.toast(msg)
#                 return
#         except Exception:
#             pass
#             # DB unavailable or not seeded yet -> greet from claims only
#         oid, upn, display_name, _groups = _extract_identity(principal)
#         if display_name:
#             st.session_state["_auth_source"] = "entra"
#             st.session_state["_principal_name"] = display_name or (upn.split("@")[0] if upn else None)
#             st.session_state["_principal_upn"] = upn 
#             st.session_state["_principal_oid"] = oid 
#             st.success(f"Welcome, {display_name}")
#             st.caption("Signed in with Microsoft Entra. App features will appear once the database connection & access are ready")
#             return
#         st.info("You're signed in with Microsoft, but we couldn't load access yet.")
#         return
    


    # email = _extract_email_from_principal(principal)

    # if email:
    #     success,  message = authenticate_user(email)
    #     if success:
    #         st.session_state["_auth_source"] = "entra"
    #         st.toast(f"Signed in as {email}")
    #         return 
        
    # if "user_id" not in st.session_state:
    #     principal = _easy_auth_principal()
    #     if principal:
    #         email = None
    #         for claim in principal.get("claims", []):
    #             if claim.get("typ") in ("https://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    #                                     "emails",
    #                                     "name"):
    #                 email = claim.get("val")
    #                 break
    #         email = email or os.environ.get("X_MS_CLIENT_PRINCIPAL_NAME")
    #         if email:
    #             success, message = authenticate_user(email)
    #             if success:
    #                 st.session_state["_auth_source"] = "entra"
    #                 st.toast(f"Signed in as {email}")
    #                 return 
                
    # if "user_id" in st.session_state:
    #     return 

    # ------------- ORIGINAL -------------
    
    # with st.form("login_form"):
    #     st.subheader("🔐 Please log in to continue")
    #     email = st.text_input("Email address", placeholder="you@company.com")

    #     submitted = st.form_submit_button("Login")
    #     if submitted and email:
    #         success, message = authenticate_user(email)
    #         if success:
    #             st.success(message)
    #             st.rerun()
    #         else: st.error(message)


# components/common/login_widget.py
import os, json, base64, streamlit as st
from utils.auth import authenticate_principal, _extract_identity

_PRINCIPAL_CACHE_KEY = "_principal_json"

def _server_principal() -> dict | None:
    """
    Easy Auth sets X_MS_CLIENT_PRINCIPAL (base64 JSON) on each request in App Service.
    Streamlit doesn't expose request headers directly, but for many setups App Service
    also forwards this value into the container environment. If present, prefer it.
    """
    raw = os.environ.get("X_MS_CLIENT_PRINCIPAL")
    if not raw:
        return None
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        return None

def _client_principal(key: str) -> dict | None:
    """
    Browser-side fetch of /.auth/me with credentials. Cached in session.
    Requires no extra packages (uses Streamlit's built-in iframe eval via markdown+JS).
    """
    # Cached?
    if _PRINCIPAL_CACHE_KEY in st.session_state:
        return st.session_state[_PRINCIPAL_CACHE_KEY]

    # Tiny inline JS fetcher; returns JSON as a string into a hidden <textarea>.
    # We then read it back from st.session_state via st.text_area with a unique key.
    fetch_id = f"_auth_fetch_{key}"
    placeholder = st.empty()
    placeholder.markdown(
        f"""
        <script>
        (async function() {{
          try {{
            const urls = ["/.auth/me", (window.location.origin||"")+"/.auth/me"];
            let data = null;
            for (const u of urls) {{
              try {{
                const r = await fetch(u, {{ credentials: "include", cache: "no-store" }});
                if (r.ok) {{ data = await r.text(); break; }}
              }} catch (e) {{}}
            }}
            const el = document.getElementById("{fetch_id}");
            if (el) {{
              el.value = data || "";
              el.dispatchEvent(new Event("input", {{ bubbles: true }}));
            }}
          }} catch (e) {{}}
        }})();
        </script>
        <textarea id="{fetch_id}" style="display:none"></textarea>
        """,
        unsafe_allow_html=True,
    )
    raw = st.text_area("",
                       key=fetch_id,
                       label_visibility="collapsed",
                       height=1)  # hidden but binds state
    placeholder.empty()

    if not raw:
        return None
    try:
        principal = json.loads(raw)
        st.session_state[_PRINCIPAL_CACHE_KEY] = principal
        return principal
    except Exception:
        return None

def _get_principal() -> dict | None:
    # Try server header first
    p = _server_principal()
    if p:
        st.session_state[_PRINCIPAL_CACHE_KEY] = p
        return p
    # Fallback to client fetch
    return _client_principal(key="auth_me")

def login_widget():
    # Already fully authed via DB?
    if "user_id" in st.session_state:
        return

    principal = _get_principal()

    if principal:
        # Try full DB-based auth first (creates/updates user, loads access)
        try:
            ok, msg = authenticate_principal(principal, mode="autoprovision")
            if ok:
                st.toast(msg)
                return
        except Exception:
            pass  # DB might not be ready; we still greet below.

        # Greet from claims (no DB)
        oid, upn, display_name, _groups = _extract_identity(principal)
        if display_name or upn:
            st.session_state["_auth_source"] = "entra"
            st.session_state["_principal_name"] = display_name or (upn.split("@")[0] if upn else None)
            st.session_state["_principal_upn"] = upn
            st.session_state["_principal_oid"] = oid
        return

    # No principal detected: show a sign-in hint (the top Login button also works)
    st.info("Sign-in required. Click the **Login** button above if you aren't redirected automatically.")

def debug_auth_panel():
    """
    Optional: call from Main.py to show what we actually see. This avoids duplicate keys.
    """
    with st.expander("Debug • Authentication (remove after testing)"):
        env_present = bool(os.environ.get("X_MS_CLIENT_PRINCIPAL"))
        st.write(f"Server header present: **{env_present}**")
        principal = st.session_state.get(_PRINCIPAL_CACHE_KEY) or _get_principal()
        st.code(json.dumps(principal, indent=2) if principal else "No principal")
        if principal:
            from utils.auth import _extract_identity
            oid, upn, display_name, groups = _extract_identity(principal)
            st.json({
                "parsed": {"oid": oid, "upn": upn, "display_name": display_name, "groups_count": len(groups)}
            })
