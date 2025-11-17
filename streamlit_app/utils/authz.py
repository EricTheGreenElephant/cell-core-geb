from __future__ import annotations
import streamlit as st
from functools import wraps
from typing import Callable
from utils.access_bootstrap import ensure_user_and_access


_ACCESS_ORDER = {"Read": 1, "Write": 2, "Admin": 3}

def _has_level(actual: str | None, need: str) -> bool:
    if not actual: 
        return False 
    return _ACCESS_ORDER.get(actual, 0) >= _ACCESS_ORDER[need]

@st.cache_data(ttl=300)
def get_permissions_cached(user_id: int, group_oids: tuple[str, ...]) -> dict[str, str]:
    """
    Returns { area_name: access_level } from st.session_state if available,
    otherwise recomputes via ensure_user_and_access().
    """
    if "access" in st.session_state:
        return dict(st.session_state["access"])
    
    _, access = ensure_user_and_access()
    return access

def require_areas(area: str, minimum_level: str = "Read") -> Callable:
    """ 
    Decorator to gate a page/section by named area + minimum level 
    Example:
        @require_areas("Production", minimum_level="Write")
        def page():
            ...
    """
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Ensure session_state is primed for this request:
            user_id, access_map = ensure_user_and_access()
            level = access_map.get(area)
            if not _has_level(level, minimum_level):
                st.error("You don't have access to this page.")
                st.caption(f"Required: {area} ({minimum_level})")
                st.stop()
            return fn(*args, **kwargs)
        return wrapper
    return decorator