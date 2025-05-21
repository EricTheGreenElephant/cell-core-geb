from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FilamentMountingModel(BaseModel):
    id: Optional[int]
    filament_id: int
    printer_id: int
    mounted_by: int
    mounted_at: Optional[datetime] = None
    unmounted_at: Optional[datetime] = None
    unmounted_by: Optional[int] = None
    remaining_weigth: float
    status: str