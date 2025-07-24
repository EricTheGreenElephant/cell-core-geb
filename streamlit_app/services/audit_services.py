import re
from db.base import Base
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.types import Float, Numeric, DECIMAL
from schemas.audit_schemas import FieldChangeAudit
from utils.db_transaction import transactional
from constants.audit_constants import ALLOWED_AUDIT_TABLES


def get_model_class_by_table_name(table_name: str):
    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        if hasattr(model_class, "__tablename__") and model_class.__tablename__ == table_name:
            return model_class
    return None

def update_record_with_audit(db: Session, data: FieldChangeAudit, update: bool = True):
    model_class = get_model_class_by_table_name(data.table)

    is_float_field = False

    if model_class:
        try:
            column = model_class.__table__.columns[data.field]
            if isinstance(column.type, (Float, Numeric, DECIMAL)):
                is_float_field = True
        except Exception:
            pass
    
    if is_float_field:
        try:
            old_float = round(float(data.old_value), 5) if data.old_value is not None else None
            new_float = round(float(data.new_value), 5) if data.new_value is not None else None
            if old_float == new_float:
                return
        except Exception:
            pass
    
    else:
        if str(data.old_value) == str(data.new_value):
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
