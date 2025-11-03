from sqlalchemy.orm import Session
from sqlalchemy import select, text
from models.filament_models import FilamentMounting
from schemas.filament_mount_schemas import FilamentMountOut
from schemas.audit_schemas import FieldChangeAudit
from services.audit_services import update_record_with_audit
from utils.db_transaction import transactional


@transactional
def get_mounts_with_filaments(db: Session) -> list[FilamentMountOut]:
    mounts = db.scalars(
        select(FilamentMounting).where(FilamentMounting.unmounted_at.is_(None)).order_by(FilamentMounting.id)
    ).all()
    return [FilamentMountOut.model_validate(m) for m in mounts]

@transactional
def get_unmounted_mounts(db: Session) -> list[dict]:
    sql = """
        SELECT
            fm.id AS mount_id,
            f.serial_number,
            p.name AS printer_name,
            fm.remaining_weight,
            fm.unmounted_at,
            fm.status,
            fm.unmounted_by
        FROM filament_mounting fm
        JOIN filaments f ON fm.filament_tracking_id = f.id
        JOIN printers p ON fm.printer_id = p.id
        WHERE fm.unmounted_at IS NOT NULL
        ORDER BY fm.unmounted_at DESC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_mount_fields(
    db: Session,
    mount_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="filament_mounting",
            record_id=mount_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
    db.commit()