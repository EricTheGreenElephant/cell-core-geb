# import pyodbc
# from utils.db import db_connection

# def get_user_access(user_id):
#     try: 
#         with db_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute("""
#                         SELECT a.area_name, ar.access_level
#                         FROM access_rights ar
#                         JOIN application_areas a ON a.id = ar.area_id
#                         WHERE ar.user_id = ? 
#                         """, (user_id))
#             rows = cursor.fetchall()
#             return {row[0]: row[1] for row in rows}
#     except pyodbc.Error as e:
#         print(f"[ACCESS ERROR] {e}")
#         return []
    
from sqlalchemy import select 
from db.orm_session import get_session
from models.lifecycle_stages_models import ApplicationArea, AccessRight
from models.users_models import GroupAreaRight

_ACCESS_ORDER = {"Read": 1, "Write": 2, "Admin": 3}

def get_effective_access(user_id: int, group_oids: list[str]) -> dict[str, str]:
    """
    Returns { area_name: access_level } by union of:
      - user-specific rights (access_rights)
      - group-derived rights (group_area_rights)
    with Admin > Write > Read precedence per area.
    """
    with get_session() as db:
        user_rows = db.execute(
            select(ApplicationArea.area_name, AccessRight.access_level)
            .join(AccessRight, AccessRight.area_id == ApplicationArea.id)
            .where(AccessRight.user_id == user_id)
        ).all()

        group_rows = []
        if group_oids:
            group_rows = db.execute(
                select(ApplicationArea.area_name, GroupAreaRight.access_level)
                .join(GroupAreaRight, GroupAreaRight.area_id == ApplicationArea.id)
                .where(GroupAreaRight.group_oid.in_(group_oids))
            ).all()

        merged: dict[str, str] = {}
        for area, level in user_rows + group_rows:
            if area not in merged:
                merged[area] = level 
            else:
                merged[area] = max(merged[area], level, key=_ACCESS_ORDER.get)
        return merged

def get_user_access(user_id: int) -> dict[str, str]:
    with get_session() as db:
        rows = db.execute(
            select(ApplicationArea.area_name, AccessRight.access_level)
            .join(AccessRight, AccessRight.area_id == ApplicationArea.id)
            .where(AccessRight.user_id == user_id)
        ).all()
        return {area_name: access_level for area_name, access_level in rows}