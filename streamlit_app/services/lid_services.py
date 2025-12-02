from sqlalchemy.orm import Session
from sqlalchemy import text
from models.lid_models import Lid
from schemas.lid_schemas import LidCreate, LidOut
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from utils.db_transaction import transactional


@transactional
def insert_lids(db: Session, data: LidCreate) -> LidOut:
    new_lid = Lid(**data.model_dump())
    db.add(new_lid)
    db.commit()
    db.refresh(new_lid)
    return LidOut.model_validate(new_lid)

@transactional
def get_lid_inventory(db: Session) -> list[dict]:
    sql = "SELECT * FROM v_lid_inventory WHERE serial_number <> 'LEGACY_SEAL' ORDER BY received_at DESC"
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def get_available_lid_batches(db: Session) -> list[dict]:
    sql = """
        SELECT id, serial_number
        FROM lids
        WHERE qc_result = 'PASS'
            AND serial_number <> 'LEGACY_LID'
        ORDER BY received_at DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_lid_fields(
    db: Session,
    lid_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="lids",
            record_id=lid_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id

        )
        update_record_with_audit(db, audit)
    db.commit()

@transactional
def get_all_lids(db: Session) -> list[LidOut]:
    lids = db.query(Lid).order_by(Lid.received_at.desc()).all()
    return [LidOut.model_validate(l) for l in lids]