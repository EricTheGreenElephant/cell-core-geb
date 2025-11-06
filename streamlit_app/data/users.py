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
    
from sqlalchemy import select, insert, update
from db.orm_session import get_session
from models.users_models import User 


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
        
        new_id = db.execute(
            insert(User)
            .values(
                azure_ad_object_id=oid,
                user_principal_name=(upn or None),
                display_name=(display_name or (upn or "User")),
                is_active=True,
            )
            .returning(User.id)
        ).scalar_one()

        db.commit()
        return (new_id, display_name or (upn or "User"))