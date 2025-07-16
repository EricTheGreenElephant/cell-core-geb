from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base
from models.lifecycle_stages_models import LifecycleStages
from models.storage_locations_models import StorageLocation


class ProductType(Base):
    __tablename__ = 'product_types'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    average_weight = Column(Integer)
    buffer_weight = Column(Integer)


class ProductRequest(Base):
    __tablename__ = 'product_requests'
    id = Column(Integer, primary_key=True)
    requested_by = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('product_types.id'))
    lot_number = Column(String)
    status = Column(String, default="Pending")
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String)

    product = relationship("models.production_models.ProductType")


class ProductHarvest(Base):
    __tablename__ = 'product_harvest'
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('product_requests.id'))
    filament_mounting_id = Column(Integer, ForeignKey('filament_mounting.id'))
    printed_by = Column(Integer, ForeignKey('users.id'))
    print_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    lid_id = Column(Integer, ForeignKey('lids.id'))
    seal_id = Column(String(50), nullable=False)


class ProductTracking(Base):
    __tablename__ = 'product_tracking'
    id = Column(Integer, primary_key=True)
    harvest_id = Column(Integer, ForeignKey('product_harvest.id'), unique=True, nullable=False)
    tracking_id = Column(String(50), unique=True, nullable=False)
    previous_stage_id = Column(Integer, ForeignKey('lifecycle_stages.id'), nullable=True)
    current_stage_id = Column(Integer, ForeignKey('lifecycle_stages.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('storage_locations.id'), nullable=True)
    last_updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    stage = relationship('models.lifecycle_stages_models.LifecycleStages', foreign_keys=[current_stage_id])
    previous_stage = relationship('LifecycleStages', foreign_keys=[previous_stage_id], backref="previous_stage_products")
    location = relationship('models.storage_locations_models.StorageLocation')
    treatment_batch_product = relationship("models.logistics_models.TreatmentBatchProduct", back_populates="product", uselist=False)
    post_treatment_inspections = relationship("PostTreatmentInspection", back_populates="product")
    quality_controls = relationship("models.product_quality_control_models.ProductQualityControl", back_populates='product')
    investigation = relationship("ProductInvestigation", back_populates="product", uselist=False)
    status_history = relationship("ProductStatusHistory", back_populates="product")
    quarantine_records = relationship("QuarantinedProducts", back_populates="product")

class ProductStatusHistory(Base):
    __tablename__ = "product_status_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product_tracking.id"), nullable=False)
    from_stage_id = Column(Integer, ForeignKey("lifecycle_stages.id"), nullable=True)
    to_stage_id = Column(Integer, ForeignKey("lifecycle_stages.id"), nullable=False)
    reason = Column(String(255), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    product = relationship("ProductTracking", back_populates="status_history")
    from_stage = relationship("LifecycleStages", foreign_keys=[from_stage_id])
    to_stage = relationship("LifecycleStages", foreign_keys=[to_stage_id])
    user = relationship("User", back_populates="status_changes")
    