from pydantic import BaseModel
from typing import Any


class FieldChangeAudit(BaseModel):
    table: str
    record_id: int
    field: str
    old_value: Any
    new_value: Any
    reason: str
    changed_by: int

    