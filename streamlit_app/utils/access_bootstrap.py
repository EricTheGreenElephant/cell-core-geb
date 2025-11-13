from __future__ import annotations
import streamlit as st
from utils.auth import get_current_user
from utils.groups import get_group_oids
from data.users import upsert_user_by_oid
from data.access import get_effective_access


def ensure_user_and_access():
    """
    - Reads current EasyAuth user
    - Upserts the user record by Entra OID
    - Resolves effective access by combining user + group rights
    - Caches into st.session_state["user_id"], ["display_name"], ["group_oids"], ["access"]
    """
    user = get_current_user()
    if not user:
        st.warning("Please sign in.")
        st.stop()

    # Gather identity info
    oid = user.get("oid")
    upn = user.get("email") or user.get("name")
    display_name = user.get("name") or upn or "User"

    if not oid:
        st.error("Missing Entra object id (oid) in authentication claims.")
        st.stop()
    
    # Persist/refresh user record
    user_id, disp = upsert_user_by_oid(oid=oid, upn=upn, display_name=display_name)

    # Resolve groups from headers
    groups = sorted(get_group_oids())
    # Compute effective access map from DB
    access_map = get_effective_access(user_id=user_id, group_oids=groups)

    # Prime session_state 
    st.session_state["user_id"] = user_id
    st.session_state["display_name"] = disp
    st.session_state["group_oids"] = groups
    st.session_state["access"] = access_map

    return user_id, access_map 

