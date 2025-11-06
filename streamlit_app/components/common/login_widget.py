import os
import json
import base64
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from utils.auth import authenticate_user, authenticate_principal, _extract_identity



_PRINCIPAL_CACHE_KEY = "_principal_json"

_FETCH_JS = r"""
async function getPrincipal() {
  const urls = [
    "/.auth/me",
    (window.location.origin || "") + "/.auth/me",
    "./.auth/me"
  ];
  for (const u of urls) {
    try {
      const r = await fetch(u, { credentials: "include", cache: "no-store" });
      if (!r.ok) continue;
      const text = await r.text();
      // Return raw text to Python; we'll parse there.
      return text;
    } catch (e) { /* try next */ }
  }
  return null;
}
return await getPrincipal();
"""

def _fetch_principal_via_auth_me(key: str) -> dict | None:
    # Runs in the browser, can fetch /.auth/me (cookie session present)
    if _PRINCIPAL_CACHE_KEY in st.session_state:
        return st.session_state[_PRINCIPAL_CACHE_KEY]
    
    raw = streamlit_js_eval(js_code=_FETCH_JS, key=key)
    if not raw:
        return None
    
    try:
        principal = json.loads(raw)
    except Exception:
        try:
            principal = json.loads(str(raw))
        except Exception:
            return None
        
    st.session_state[_PRINCIPAL_CACHE_KEY] = principal
    return principal
    
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
    
def login_widget():
    """Reusable login form that only display if user is not logged in."""

    if "user_id" in st.session_state:
        return
    
    principal = _fetch_principal_via_auth_me(key="auth_me_login_v2")
    if principal:
        try:
            ok, msg = authenticate_principal(principal, mode="autoprovision")
            if ok: 
                st.toast(msg)
                return
        except Exception:
            pass
            # DB unavailable or not seeded yet -> greet from claims only
        oid, upn, display_name, _groups = _extract_identity(principal)
        if display_name:
            st.session_state["_auth_source"] = "entra"
            st.session_state["_principal_name"] = display_name or (upn.split("@")[0] if upn else None)
            st.session_state["_principal_upn"] = upn 
            st.session_state["_principal_oid"] = oid 
            st.success(f"Welcome, {display_name}")
            st.caption("Signed in with Microsoft Entra. App features will appear once the database connection & access are ready")
            return
        st.info("You're signed in with Microsoft, but we couldn't load access yet.")
        return
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

    # --- Manual paste fallback so you can proceed today ---
    with st.expander("Troubleshoot: Paste /.auth/me JSON (temporary)"):
        st.caption("Open /.auth/me in a new tab, copy all JSON, paste below, and click Use principal.")
        pasted = st.text_area("Paste /.auth/me JSON here")
        if st.button("Use principal"):
            try:
                principal = json.loads(pasted)
                st.session_state[_PRINCIPAL_CACHE_KEY] = principal
                # Try normal path once more
                try:
                    ok, msg = authenticate_principal(principal, mode="autoprovision")
                    if ok:
                        st.success(msg); st.rerun()
                        return
                except Exception:
                    pass
                # Claims-only greeting
                oid, upn, display_name, _groups = _extract_identity(principal)
                if display_name or upn:
                    st.session_state["_auth_source"] = "entra"
                    st.session_state["_principal_name"] = display_name or (upn.split("@")[0] if upn else None)
                    st.session_state["_principal_upn"] = upn
                    st.session_state["_principal_oid"] = oid
                    st.success(f"Welcome, {display_name or upn}")
                    st.rerun()
            except Exception as e:
                st.error(f"Could not parse pasted JSON: {e}")
    
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

            