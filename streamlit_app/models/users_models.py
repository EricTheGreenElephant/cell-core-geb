from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.base import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    azure_ad_object_id = Column(String(255), unique=True, nullable=False)
    user_principal_name = Column(String(255), nullable=True)
    display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


    received_filaments = relationship("models.filament_models.Filament", back_populates="received_user", foreign_keys="Filament.received_by")
    mounted_filaments = relationship("models.filament_models.FilamentMounting", back_populates="mounted_by_user", foreign_keys="FilamentMounting.mounted_by")
    unmounted_filaments = relationship("models.filament_models.FilamentMounting", back_populates="unmounted_by_user", foreign_keys="FilamentMounting.unmounted_by")
    received_lids = relationship("models.lid_models.Lid", back_populates="receiver", foreign_keys="Lid.received_by")
    post_treatment_inspections = relationship("PostTreatmentInspection", back_populates="inspector")
    investigations_created = relationship("ProductInvestigation", back_populates="created_user")
    status_changes = relationship("ProductStatusHistory", back_populates="user")