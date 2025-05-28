from pydantic import BaseModel
from datetime import datetime


class UserOut(BaseModel):
    id: int
    display_name: str
    created_at: datetime

    class Config:
        from_attributes = True
