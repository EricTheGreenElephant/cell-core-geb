import re
from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.audit_schemas import FieldChangeAudit
from utils.db_transaction import transactional
from constants.audit_constants import ALLOWED_AUDIT_TABLES


def update_record_with_audit(db: Session, data: FieldChangeAudit, update: bool = True):
    if data.old_value == data.new_value:
        return
    
    if data.table not in ALLOWED_AUDIT_TABLES:
        raise ValueError("Unauthorized table")
    
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", data.field):
        raise ValueError("Unsafe field name")
    
    if update:
        db.execute(text(
            f"UPDATE {data.table} SET {data.field} = :val WHERE id = :rid"
        ), {"val": data.new_value, "rid": data.record_id})

    db.execute(
        text("""
        INSERT INTO audit_log (table_name, record_id, field_name, old_value, new_value, reason, changed_by)
        VALUES (:t, :r, :f, :o, :n, :rsn, :u)
        """),
        {
            "t": data.table,
            "r": data.record_id,
            "f": data.field,
            "o": str(data.old_value),
            "n": str(data.new_value),
            "rsn": data.reason,
            "u": data.changed_by
        }
    )
