from sqlalchemy.orm import Session
from sqlalchemy import text
from models.seal_models import Seal
from schemas.seals_schemas import SealCreate, SealOut
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from utils.db_transaction import transactional


@transactional
def insert_seals(db: Session, data: SealCreate) -> SealOut:
    new_seal = Seal(**data.model_dump())
    db.add(new_seal)
    db.commit()
    db.refresh(new_seal)
    return SealOut.model_validate(new_seal)

@transactional
def get_seal_inventory(db: Session) -> list[dict]:
    sql = "SELECT * FROM v_seal_inventory ORDER BY received_at DESC"
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def get_available_seal_batches(db: Session) -> list[dict]:
    sql = """
        SELECT id, serial_number, quantity
        FROM seals
        WHERE qc_result = 'PASS'
        ORDER BY received_at DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_seal_fields(
    db: Session,
    seal_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="seals",
            record_id=seal_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id

        )
        update_record_with_audit(db, audit)
    db.commit()

@transactional
def get_all_seals(db: Session) -> list[SealOut]:
    seals = db.query(Seal).order_by(Seal.received_at.desc()).all()
    return [SealOut.model_validate(s) for s in seals]