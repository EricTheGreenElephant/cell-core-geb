from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
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
    is_active = Column(Boolean, nullable=False, default=True)


    received_filaments = relationship("models.filament_models.Filament", back_populates="received_user", foreign_keys="Filament.received_by")
    mounted_filaments = relationship("models.filament_models.FilamentMounting", back_populates="mounted_by_user", foreign_keys="FilamentMounting.mounted_by")
    unmounted_filaments = relationship("models.filament_models.FilamentMounting", back_populates="unmounted_by_user", foreign_keys="FilamentMounting.unmounted_by")
    received_lids = relationship("models.lid_models.Lid", back_populates="receiver", foreign_keys="Lid.received_by")
    received_seals = relationship("Seal", back_populates="seal_receiver", foreign_keys="Seal.received_by")
    post_treatment_inspections = relationship("PostTreatmentInspection", back_populates="inspector")
    investigations_created = relationship("ProductInvestigation", back_populates="created_user")
    status_changes = relationship("ProductStatusHistory", back_populates="user")
    quarantines_created = relationship("QuarantinedProducts", foreign_keys="[QuarantinedProducts.quarantined_by]", back_populates="quarantined_user")
    quarantines_resolved = relationship("QuarantinedProducts", foreign_keys="[QuarantinedProducts.resolved_by]", back_populates="resolved_user")
    material_usages = relationship("MaterialUsage", back_populates="user")


class ApplicationArea(Base):
    __tablename__ = 'application_areas'
    
    id = Column(Integer, primary_key=True)
    area_name = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class GroupAreaRight(Base):
    __tablename__ = "group_area_rights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_oid = Column(UNIQUEIDENTIFIER, nullable=False)
    area_id = Column(Integer, nullable=False)
    access_level = Column(String(20), nullable=False)
