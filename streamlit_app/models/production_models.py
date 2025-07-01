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
    current_stage_id = Column(Integer, ForeignKey('lifecycle_stages.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('storage_locations.id'), nullable=True)
    last_updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    stage = relationship('models.lifecycle_stages_models.LifecycleStages')
    location = relationship('models.storage_locations_models.StorageLocation')
    treatment_batch_product = relationship("models.logistics_models.TreatmentBatchProduct", back_populates="product", uselist=False)
    post_treatment_inspections = relationship("PostTreatmentInspection", back_populates="product")
    quality_controls = relationship("models.product_quality_control_models.ProductQualityControl", back_populates='product')
    