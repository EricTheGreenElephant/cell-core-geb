from pydantic import BaseModel
from typing import Optional


class StorageLocationModel(BaseModel):
    id: Optional[int]
    location_name: str
    location_type: str
    description: Optional[str] = None