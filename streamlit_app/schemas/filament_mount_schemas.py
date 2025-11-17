from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from schemas.filament_schemas import FilamentOut
from schemas.printer_schemas import PrinterOut


class FilamentMountOut(BaseModel):
    id: int
    filament_tracking_id: int
    printer_id: int
    mounted_by: int
    remaining_weight: float
    mounted_at: datetime
    status: str
    unmounted_by: Optional[int]
    unmounted_at: Optional[datetime]
    filament: FilamentOut
    printer: PrinterOut

    model_config = ConfigDict(from_attributes=True)