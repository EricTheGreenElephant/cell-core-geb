from sqlalchemy.orm import Session
from sqlalchemy import select
from models.printers_models import Printer
from schemas.printer_schemas import PrinterOut
from utils.db_transaction import transactional


@transactional
def get_printers(db: Session) -> list[PrinterOut]:
    printers = db.scalars(select(Printer).order_by(Printer.name)).all()
    return [PrinterOut.model_validate(p) for p in printers]