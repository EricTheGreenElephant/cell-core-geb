from __future__ import annotations    
from sqlalchemy import select 
from db.orm_session import get_session
from models.users_models import GroupAreaRight, ApplicationArea

_ACCESS_ORDER = {"Read": 1, "Write": 2, "Admin": 3}

def get_effective_access(user_id: int, group_oids: list[str]) -> dict[str, str]:
    """
    Returns { area_name: access_level } based *only* on group-derived rights
    (dbo.group_area_rights), ignoring any legacy per-user access.
    """
    with get_session() as db:
        if not group_oids:
            return {}
        
        rows = db.execute(
            select(ApplicationArea.area_name, GroupAreaRight.access_level)
            .join(GroupAreaRight, GroupAreaRight.area_id == ApplicationArea.id)
            .where(GroupAreaRight.group_oid.in_(group_oids))
        ).all()

        merged: dict[str, str] = {}

        def better(current: str | None, incoming: str) -> str:
            if not current:
                return incoming
            return incoming if _ACCESS_ORDER[incoming] > _ACCESS_ORDER[current] else current
        
        for area_name, level in rows:
            merged[area_name] = better(merged.get(area_name), level)

        return merged 
    
def get_user_access(user_id: int) -> dict[str, str]:
    """
    Legacy helper; kept if old code still imports it.
    Returns empty dict
    """
    return {}