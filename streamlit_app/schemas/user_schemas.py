from pydantic import BaseModel, ConfigDict
from datetime import datetime


class UserOut(BaseModel):
    id: int
    display_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
