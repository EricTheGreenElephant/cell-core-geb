from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, text, and_
from typing import Optional
from datetime import datetime, timezone
from services.audit_services import update_record_with_audit
from models.filament_models import (
    Filament,
    FilamentMounting,
    FilamentAcclimatization
)
from models.storage_locations_models import StorageLocation
from models.printers_models import Printer
from models.users_models import User
from schemas.filament_schemas import (
    FilamentCreate,
    FilamentOut,
    FilamentAcclimatizationOut
)
from schemas.storage_location_schemas import StorageLocationOut
from schemas.printer_schemas import PrinterOut
from schemas.audit_schemas import FieldChangeAudit
from utils.db_transaction import transactional

@transactional
def insert_filament(db: Session, data: FilamentCreate) -> FilamentOut:
    new_filament = Filament(**data.model_dump())
    db.add(new_filament)
    db.commit()
    db.refresh(new_filament)
    return FilamentOut.model_validate(new_filament)

@transactional
def get_storage_locations(db: Session) -> list[StorageLocationOut]:
    locations = db.scalars(select(StorageLocation).order_by(StorageLocation.location_name)).all()
    return [StorageLocationOut.model_validate(loc) for loc in locations]

@transactional
def get_all_filament_statuses(db: Session) -> list[dict]:
    sql = "SELECT * FROM v_filament_status ORDER BY filament_id"
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def get_filaments_not_acclimatizing(db: Session) -> list[dict]:
    sql = """
        SELECT id, filament_id, serial_number FROM v_filament_status
        WHERE qc_result = 'PASS'
        AND current_status = 'In Storage';
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def insert_filament_acclimatization(db: Session, filament_id: int, user_id: int):
    accl = FilamentAcclimatization(
        filament_tracking_id=filament_id,
        status="Acclimatizing",
        moved_at=datetime.now(timezone.utc),
        moved_by=user_id
    )
    db.add(accl)
    db.commit()

@transactional
def get_acclimatized_filaments(db: Session) -> list[dict]:
    sql = """
        SELECT f.id, f.filament_id, f.serial_number, f.weight_grams,
            a.id AS acclimatization_id, a.ready_at, loc.location_name
        FROM filament_acclimatization a
        JOIN filaments f ON a.filament_tracking_id = f.id
        JOIN storage_locations loc ON f.location_id = loc.id
        WHERE a.ready_at <= GETDATE()
        AND a.status = 'Acclimatizing'
        AND NOT EXISTS (
            SELECT 1 FROM filament_mounting m WHERE m.filament_tracking_id = f.id
        )
        ORDER BY a.ready_at ASC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def restore_acclimatizing_filaments(db: Session) -> list[dict]:
    sql = """
        SELECT f.id, f.filament_id, f.serial_number, f.weight_grams,
            a.id AS acclimatization_id, a.ready_at, loc.location_name
        FROM filament_acclimatization a
        JOIN filaments f ON a.filament_tracking_id = f.id
        JOIN storage_locations loc ON f.location_id = loc.id
        WHERE a.status = 'Acclimatizing'
        AND NOT EXISTS (
            SELECT 1 FROM filament_mounting m WHERE m.filament_tracking_id = f.id
        )
        ORDER BY a.ready_at ASC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def get_available_printers(db: Session) -> list[PrinterOut]:
    subquery = select(FilamentMounting.printer_id).where(FilamentMounting.unmounted_at.is_(None))
    stmt = (
        select(Printer)
        .where(Printer.status == 'Active')
        .where(Printer.id.not_in(subquery))
    )
    printers = db.scalars(stmt).all()
    return [PrinterOut.model_validate(p) for p in printers]

@transactional
def insert_filament_mount(
        db: Session,
        filament_id: int,
        printer_id: int,
        mounted_by: int,
        acclimatization_id: int
):
    filament = db.get(Filament, filament_id)
    if not filament:
        raise ValueError("Filament not found")
    
    mounting = FilamentMounting(
        filament_tracking_id=filament_id,
        printer_id=printer_id,
        mounted_by=mounted_by,
        remaining_weight=filament.weight_grams,
        mounted_at=datetime.now(timezone.utc)
    )
    db.add(mounting)

    stmt = (
        update(FilamentAcclimatization)
        .where(FilamentAcclimatization.id == acclimatization_id)
        .values(status='Complete')
    )
    db.execute(stmt)
    db.commit()

@transactional
def get_mounted_filaments(db: Session) -> list[dict]:
    sql = """
        SELECT
            fm.id AS mount_id,
            f.filament_id,
            f.serial_number,
            p.name AS printer_name,
            fm.remaining_weight
        FROM filament_mounting fm
        JOIN filaments f ON fm.filament_tracking_id = f.id
        JOIN printers p ON fm.printer_id = p.id
        WHERE fm.status = 'In Use'
        ORDER BY p.name
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def unmount_filament(db: Session, mount_id: int, user_id: int):
    stmt = (
        update(FilamentMounting)
        .where(FilamentMounting.id == mount_id)
        .values(
            unmounted_at=datetime.now(timezone.utc),
            unmounted_by=user_id,
            status="Unmounted"
        )
    )
    db.execute(stmt)
    db.commit()

@transactional
def get_mountable_filament_mounts(db: Session, required_weight: float) -> list[dict]:
    sql = """
        SELECT
            fm.id,
            f.filament_id,
            f.serial_number,
            p.name AS printer_name,
            fm.remaining_weight
        FROM filament_mounting fm
        JOIN filaments f ON fm.filament_tracking_id = f.id
        JOIN printers p ON fm.printer_id = p.id
        WHERE fm.remaining_weight >= :weight
            AND fm.status = 'In Use'
    """
    result = db.execute(text(sql), {"weight": required_weight})
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

@transactional
def update_filament_fields(
    db: Session,
    filament_id: int,
    updates: dict[str, tuple],
    reason: str,
    user_id: int
):
    for field, (old_value, new_value) in updates.items():
        audit = FieldChangeAudit(
            table="filaments",
            record_id=filament_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit)
    db.commit()

@transactional
def get_filaments(db: Session) -> list[FilamentOut]:
    filaments = db.scalars(select(Filament).order_by(Filament.id)).all()
    return [FilamentOut.model_validate(f) for f in filaments]

@transactional
def search_filament(db: Session, filament_id: int) -> Optional[dict]:
    """
    Returns filament info + computed current_weight.

    current_weight is:
      - filament_mounting.remaining_weight if an 'In Use' mount exists
      - else filaments.weight_grams if > 0
      - else None
    """
    stmt = (
        select(Filament, FilamentMounting)
        .join(
            FilamentMounting,
            and_(
                FilamentMounting.filament_tracking_id == Filament.id,
                FilamentMounting.status == "In Use",
            ),
            isouter=True,  # left join
        )
        .where(Filament.filament_id == filament_id)
        # if multiple In Use rows could exist, you might want to order_by & limit(1)
        # .order_by(FilamentMounting.mounted_at.desc())
    )

    row = db.execute(stmt).first()
    if row is None:
        return None

    filament: Filament = row[0]
    mounting: FilamentMounting | None = row[1]

    if mounting is not None:
        current_weight = mounting.remaining_weight
        weight_source = "mounting"
    elif filament.weight_grams is not None and filament.weight_grams > 0:
        current_weight = filament.weight_grams
        weight_source = "filament"
    else:
        current_weight = None
        weight_source = "none"

    return {
        "filament_pk": filament.id,            # internal PK
        "filament_id": filament.filament_id,   # external logical ID
        "serial_number": filament.serial_number,
        "mount_id": mounting.id if mounting else None,
        "current_weight": current_weight,
        "weight_source": weight_source,
    }

@transactional
def update_filament_weight(
    db: Session,
    filament_pk: int,
    new_weight: float,
    reason: str,
    user_id: int,
):
    """
    Updates the weight for a filament.

    - If there is an 'In Use' mounting row for this filament -> update fm.remaining_weight
    - Otherwise -> update f.weight_grams
    """
    # 1) Check if there is an 'In Use' mount for this filament
    mounting = db.execute(
        select(FilamentMounting)
        .where(
            FilamentMounting.filament_tracking_id == filament_pk,
            FilamentMounting.status == "In Use", 
        )
    ).scalar_one_or_none()

    if mounting is not None:
        table_name = "filament_mounting"
        record_id = mounting.id 
        field_name = "remaining_weight"
        old_value = mounting.remaining_weight
    else:
        filament = db.get(Filament, filament_pk)
        if filament is None:
            raise ValueError(f"Filament with id={filament_pk} not found")
        
        table_name = "filaments"
        record_id = filament.id
        field_name = "weight_grams"
        old_value = filament.weight_grams 

    audit = FieldChangeAudit(
        table=table_name,
        record_id=record_id,
        field=field_name,
        old_value=old_value,
        new_value=new_weight,
        reason=reason,
        changed_by=user_id,
    )

    update_record_with_audit(db, audit, update=True)

    db.commit()


    # mounting_id = db.scalar(
    #     select(FilamentMounting.id).where(
    #         FilamentMounting.filament_tracking_id == filament_pk,
    #         FilamentMounting.status == "In Use",
    #     )
    # )

    # if mounting_id is not None:
    #     # 2a) Update filament_mounting.remaining_weight
    #     stmt = (
    #         update(FilamentMounting)
    #         .where(FilamentMounting.id == mounting_id)
    #         .values(remaining_weight=new_weight)
    #     )
    # else:
    #     # 2b) Update filaments.weight_grams
    #     stmt = (
    #         update(Filament)
    #         .where(Filament.id == filament_pk)
    #         .values(weight_grams=new_weight)
    #     )

    # db.execute(stmt)
    # db.commit()

@transactional
def delete_filament_acclimatization(db: Session, acclimatization_id: int, reason: str, user_id: int):
    accl = db.get(FilamentAcclimatization, acclimatization_id)
    if not accl:
        raise ValueError("Acclimatization record not found")
    
    for field in ["status", "moved_at", "moved_by"]:
        value = getattr(accl, field)
        audit = FieldChangeAudit(
            table="filament_acclimatization",
            record_id=acclimatization_id,
            field=field,
            old_value=str(value),
            new_value="DELETED",
            reason=reason,
            changed_by=user_id
        )
        update_record_with_audit(db, audit, update=False)
    db.delete(accl)
    db.commit()