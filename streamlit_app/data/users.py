# import pyodbc
# from utils.db import db_connection

# def get_user_by_email(email):
#     try:
#         with db_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute("SELECT id, display_name FROM users WHERE user_principal_name = ?", (email,))
#             result = cursor.fetchone()
#             return result
#     except pyodbc.Error as e:
#         print(f"[DB ERROR] Failed to fetch user: {e}")
#         return None
    
from sqlalchemy import select, insert, update, text
from sqlalchemy.orm import Session
from db.orm_session import get_session
from models.users_models import User 


def _get_default_department_id(db: Session) -> int:
    """
    Returns the id of the preferred default department.
    Prefers 'GEN' (General); otherwise falls back to any active department.
    """
    row = db.execute(
        text("SELECT TOP (1) id FROM dbo.departments WHERE department_code = :code AND is_active = 1"),
        {"code": "GEN"},
    ).first()
    if row:
        return int(row.id)
    
    row = db.execute(
        text("SELECT TOP (1) id FROM dbo.departments WHERE is_active = 1 ORDER BY id")
    ).first()
    if row:
        return int(row.id)
    
    raise RuntimeError(
        "No active departments found. Seed at least one department (e.g., 'General')."
    )

def get_user_by_email(email: str):
    with get_session() as db:
        user = db.execute(
            select(User.id, User.display_name)
            .where(User.user_principal_name == email.strip().lower())
        ).first()
        return (user.id, user.display_name) if user else None 
    
def get_user_by_oid(oid: str):
    """
    Return (user_id, display_name) for a given Entra object id (oid), or None.
    """
    with get_session() as db:
        row = db.execute(
            select(User.id, User.display_name).where(User.azure_ad_object_id == oid)
        ).first()
        return (row.id, row.display_name) if row else None 
    
def upsert_user_by_oid(*, oid: str, upn: str | None, display_name: str | None):
    """
    Ensure a user exists for this Entra OID.
    - If found, refresh mutable fields (UPN, display name, is_active).
    - If not found, insert a new user. 
    Returns (user_id, display_name).
    """
    with get_session() as db:
        existing = db.execute(
            select(User.id, User.display_name).where(User.azure_ad_object_id == oid)
        ).first()

        if existing:
            db.execute(
                update(User)
                .where(User.id == existing.id)
                .values(
                    user_principal_name=(upn or None),
                    display_name=(display_name or existing.display_name),
                    is_active=True,
                )
            )
            db.commit()
            return (existing.id, display_name or existing.display_name)
        
        dept_id = _get_default_department_id(db)

        new_id = db.execute(
            insert(User)
            .values(
                department_id=dept_id,
                azure_ad_object_id=oid,
                user_principal_name=(upn or None),
                display_name=(display_name or (upn or "User")),
                is_active=True,
            )
            .returning(User.id)
        ).scalar_one()

        db.commit()
        return (new_id, display_name or (upn or "User"))