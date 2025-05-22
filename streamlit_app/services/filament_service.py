from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, text
from datetime import datetime, timezone
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
    FilamentMountOut,
    FilamentAcclimatizationOut
)
from schemas.storage_location_schemas import StorageLocationOut
from schemas.printer_schemas import PrinterOut


def insert_filament(db: Session, data: FilamentCreate) -> FilamentOut:
    new_filament = Filament(**data.model_dump())
    db.add(new_filament)
    db.commit()
    db.refresh(new_filament)
    return FilamentOut.model_validate(new_filament)

def get_storage_locations(db: Session) -> list[StorageLocationOut]:
    locations = db.scalars(select(StorageLocation).order_by(StorageLocation.location_name)).all()
    return [StorageLocationOut.model_validate(loc) for loc in locations]

def get_all_filament_statuses(db: Session) -> list[dict]:
    sql = "SELECT * FROM v_filament_status ORDER BY filament_id"
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

def get_filaments_not_acclimatizing(db: Session) -> list[dict]:
    sql = """
        SELECT f.id, f.serial_number
        FROM filaments f
        WHERE f.qc_result = 'PASS'
        AND f.id NOT IN (
            SELECT filament_id FROM filament_acclimatization
            WHERE status IN ('In Acclimatization', 'In Production')
        )
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

def insert_filament_acclimatization(db: Session, filament_id: int, user_id: int):
    accl = FilamentAcclimatization(
        filament_id=filament_id,
        status="In Acclimatization",
        moved_at=datetime.now(timezone.utc),
        moved_by=user_id
    )
    db.add(accl)
    db.commit()

def get_acclimatized_filaments(db: Session) -> list[dict]:
    sql = """
        SELECT f.id, f.serial_number, f.weight_grams,
            a.id AS acclimatization_id, a.ready_at, loc.location_name
        FROM filament_acclimatization a
        JOIN filaments f ON a.filament_id = f.id
        JOIN storage_locations loc ON f.location_id = loc.id
        WHERE a.ready_at <= GETDATE()
        AND a.status = 'In Acclimatization'
        AND NOT EXISTS (
            SELECT 1 FROM filament_mounting m WHERE m.filament_id = f.id
        )
        ORDER BY a.ready_at ASC
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

def get_available_printers(db: Session) -> list[PrinterOut]:
    subquery = select(FilamentMounting.printer_id).where(FilamentMounting.unmounted_at.is_(None))
    stmt = (
        select(Printer)
        .where(Printer.status == 'Active')
        .where(Printer.id.not_in(subquery))
    )
    printers = db.scalars(stmt).all()
    return [PrinterOut.model_validate(p) for p in printers]

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
        filament_id=filament_id,
        printer_id=printer_id,
        mounted_by=mounted_by,
        remaining_weight=filament.weight_grams,
        mounted_at=datetime.now(timezone.utc)
    )
    db.add(mounting)

    stmt = (
        update(FilamentAcclimatization)
        .where(FilamentAcclimatization.id == acclimatization_id)
        .values(status='In Production')
    )
    db.execute(stmt)
    db.commit()

def get_mounted_filaments(db: Session) -> list[dict]:
    sql = """
        SELECT
            fm.id AS mount_id,
            f.serial_number,
            p.name AS printer_name,
            fm.remaining_weight
        FROM filament_mounting fm
        JOIN filaments f ON fm.filament_id = f.id
        JOIN printers p ON fm.printer_id = p.id
        WHERE fm.unmounted_at IS NULL
        ORDER BY p.name
    """
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]

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