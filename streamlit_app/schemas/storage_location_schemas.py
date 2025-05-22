from pydantic import BaseModel, ConfigDict
from typing import Optional

class StorageLocationOut(BaseModel):
    id: int
    location_name: str
    location_type: Optional[str]
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)
