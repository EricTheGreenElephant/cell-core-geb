from pydantic import BaseModel


class LifecycleStagesRead(BaseModel):
    id: int
    stage_code: str
    stage_name: str
    stage_order: int
    is_active: bool

    class Config:
        orm_mode = True