from sqlalchemy.orm import Session
from sqlalchemy import text
from models.lid_models import Lid
from schemas.lid_schemas import LidCreate, LidOut
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
    sql = "SELECT * FROM v_lid_inventory ORDER BY received_at DESC"
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def get_available_lid_batches(db: Session) -> list[dict]:
    sql = """
        SELECT id, serial_number
        FROM lids
        WHERE qc_result = 'PASS'
        ORDER BY received_at DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]