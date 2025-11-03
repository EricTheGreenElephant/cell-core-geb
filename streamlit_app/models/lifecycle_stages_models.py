from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from db.base import Base


class LifecycleStages(Base):
    __tablename__ = 'lifecycle_stages'

    id = Column(Integer, primary_key=True)
    stage_code = Column(String(50), unique=True, nullable=False)
    stage_name = Column(String(100), nullable=False)
    stage_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    quarantined_products = relationship("QuarantinedProducts", back_populates="from_stage")


class ApplicationArea(Base):
    __tablename__ = 'application_areas'
    
    id = Column(Integer, primary_key=True)
    area_name = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    app_area_right = relationship("AccessRight", back_populates="app_area")

class AccessRight(Base):
    __tablename__ = 'access_rights'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("application_areas.id"), nullable=False)
    access_level = Column(String(20), nullable=False)

    access_right_user = relationship("User", back_populates="access_user")
    app_area = relationship("ApplicationArea", back_populates="app_area_right")