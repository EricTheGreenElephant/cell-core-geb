from sqlalchemy import select, insert, update, text
from typing import Optional
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

def _initials_part(name: str) -> str:
    """
    Take a name and return two letters in 'Xx' form (e.g. Heiko -> He)
    """
    letters = [c for c in name if c.isalpha()]
    if not letters:
        return 'Xx'
    if len(letters) == 1:
        raw = letters[0] + letters[0]
    else:
        raw = "".join(letters[:2])
    return raw[0].upper() + raw[1].lower()

def build_initials_from_display_name(display_name: Optional[str]) -> str:
    """
    Build the intial-signature from a display name.
    """
    if not display_name:
        return "XxXx"
    
    parts = display_name.strip().split()
    if not parts:
        return "XxXx"
    
    if len(parts) == 1:
        first_name = last_name = parts[0]
    else:
        first_name = parts[0]
        last_name = parts[-1]

    return _initials_part(first_name) + _initials_part(last_name)
    
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
    entra_display_name = display_name
    source_name = entra_display_name or (upn or "User")
    initials_display = build_initials_from_display_name(source_name)

    with get_session() as db:
        existing = db.execute(
            select(User.id, User.display_name).where(User.azure_ad_object_id == oid)
        ).first()

        if existing:
            if existing.display_name != initials_display:
                db.execute(
                    update(User)
                    .where(User.id == existing.id)
                    .values(
                        user_principal_name=(upn or None),
                        display_name=initials_display,
                        is_active=True,
                    )
                )
            else:
                db.execute(
                    update(User)
                    .where(User.id == existing.id)
                    .values(
                        user_principal_name=(upn or None),
                        is_active=True,
                    )
                )
            db.commit()
            return (existing.id, initials_display)
        
        dept_id = _get_default_department_id(db)

        new_id = db.execute(
            insert(User)
            .values(
                department_id=dept_id,
                azure_ad_object_id=oid,
                user_principal_name=(upn or None),
                display_name=initials_display,
                is_active=True,
            )
            .returning(User.id)
        ).scalar_one()

        db.commit()
        return (new_id, initials_display)