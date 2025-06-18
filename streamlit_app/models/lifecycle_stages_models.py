from sqlalchemy import Column, Integer, String, Boolean
from db.base import Base


class LifecycleStages(Base):
    __tablename__ = 'lifecycle_stages'

    id = Column(Integer, primary_key=True)
    stage_code = Column(String(50), unique=True, nullable=False)
    stage_name = Column(String(100), nullable=False)
    stage_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)