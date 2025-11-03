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
    
from sqlalchemy import select 
from db.orm_session import get_session
from models.users_models import User 


def get_user_by_email(email: str):
    with get_session() as db:
        user = db.execute(
            select(User.id, User.display_name)
            .where(User.user_principal_name == email.strip().lower())
        ).first()
        return (user.id, user.display_name) if user else None 