from sqlalchemy.orm import Session
from sqlalchemy import text
from utils.db_transaction import transactional


@transactional
def get_contexts(db: Session) -> list[dict]:
    result = db.execute(text("SELECT id, context_code FROM issue_contexts ORDER BY context_code"))
    return list(result.mappings().all())

@transactional
def get_reasons(db: Session, include_inactive: bool = False) -> list[dict]:
    sql = """
        SELECT id, reason_code, reason_label, category, default_outcome, severity, is_active
        FROM issue_reasons
        WHERE (:all = 1) OR (is_active = 1)
        ORDER BY category, reason_label
    """
    result = db.execute(text(sql), {"all": 1 if include_inactive else 0})
    return list(result.mappings().all())

@transactional
def upsert_reason(db: Session, *, reason_id: int | None, reason_code: str, reason_label: str, 
                  category: str, default_outcome: str | None, severity: int | None, is_active: bool) -> int:
    if reason_id:
        db.execute(text(
            """
                UPDATE issue_reasons
                SET reason_code = :code, reason_label = :label, category = :cat,
                    default_outcome = :outc, severity = :sev, is_active = :active
                WHERE id = :id
            """
        ), {"code": reason_code, "label": reason_label, "cat": category,
            "outc": default_outcome, "sev": severity, "active": 1 if is_active else 0, "id": reason_id})
        return reason_id
    
    else:
        new_id = db.execute(text(
            """
                INSERT INTO issue_reasons (reason_code, reason_label, category, default_outcome, severity, is_active)
                OUTPUT INSERTED.id
                VALUES (:code, :label, :cat, :outc, :sev, :active)
            """
        ), {"code": reason_code, "label": reason_label, "cat": category,
            "outc": default_outcome, "sev": severity, "active": 1 if is_active else 0}
        ).scalar_one()
        return new_id
    
@transactional
def get_reason_context_ids(db: Session, reason_id: int) -> list[int]:
    result = db.execute(text(
        """
            SELECT context_id FROM issue_reason_contexts WHERE reason_id = :rid
        """
    ), {"rid": reason_id})
    return list(result.scalars().all())

@transactional
def set_reason_contexts(db: Session, reason_id: int, context_ids: list[int]):
    db.execute(text("DELETE FROM issue_reason_contexts WHERE reason_id = :rid"), {"rid": reason_id})
    if context_ids:
        context_ids = list(dict.fromkeys(context_ids))
        db.execute(text(
            """
                INSERT INTO issue_reason_contexts (reason_id, context_id)
                VALUES (:rid, :cid)
            """
        ), [{"rid": reason_id, "cid": cid} for cid in context_ids])

@transactional
def toggle_reason_active(db: Session, reason_id: int, is_active: bool):
    db.execute(text("UPDATE issue_reasons SET is_active = :a WHERE id = :id"),
               {"a": 1 if is_active else 0, "id": reason_id})