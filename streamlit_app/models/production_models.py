from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base
from models.lifecycle_stages_models import LifecycleStages
from models.storage_locations_models import StorageLocation


class ProductType(Base):
    __tablename__ = 'product_types'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    skus = relationship("ProductSKU", back_populates="product_type")


class ProductSKU(Base):
    __tablename__ = 'product_skus'
    id = Column(Integer, primary_key=True)
    product_type_id = Column(Integer, ForeignKey('product_types.id'), nullable=False)
    sku = Column(String(64), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    is_serialized = Column(Boolean, nullable=False)
    is_bundle = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    product_type = relationship("ProductType", back_populates="skus")
    print_specs = relationship("SKUPrintSpecs", back_populates="sku", uselist=False)
    bom_components = relationship("SKUBom", foreign_keys="SKUBom.parent_sku_id", back_populates="parent_sku")
    bom_as_component = relationship("SKUBom", foreign_keys="SKUBom.component_sku_id", back_populates="component_sku")
    requests = relationship("ProductRequest", back_populates="sku")
    trackings = relationship("ProductTracking", back_populates="sku")


class SKUPrintSpecs(Base):
    __tablename__ = 'sku_print_specs'
    sku_id = Column(Integer, ForeignKey('product_skus.id'), primary_key=True)
    height_mm = Column(Numeric(7, 2), nullable=False)
    diameter_mm = Column(Numeric(7, 2), nullable=False)
    average_weight_g = Column(Numeric(7, 2), nullable=False)
    weight_buffer_g = Column(Numeric(4, 2), nullable=False)

    sku = relationship("ProductSKU", back_populates="print_specs")


class SKUBom(Base):
    __tablename__ = 'sku_bom'
    id = Column(Integer, primary_key=True)
    parent_sku_id = Column(Integer, ForeignKey('product_skus.id'), nullable=False)
    component_sku_id = Column(Integer, ForeignKey('product_skus.id'), nullable=False)
    component_qty = Column(Integer, nullable=False)

    parent_sku = relationship("ProductSKU", foreign_keys=[parent_sku_id], back_populates="bom_components")
    component_sku = relationship("ProductSKU", foreign_keys=[component_sku_id], back_populates="bom_as_component")


class ProductRequest(Base):
    __tablename__ = 'product_requests'
    id = Column(Integer, primary_key=True)
    requested_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    sku_id = Column(Integer, ForeignKey('product_skus.id'), nullable=False)
    lot_number = Column(String, nullable=False)
    status = Column(String, default="Pending")
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String)

    sku = relationship("ProductSKU", back_populates="requests")


class ProductHarvest(Base):
    __tablename__ = 'product_harvest'
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('product_requests.id'))
    filament_mounting_id = Column(Integer, ForeignKey('filament_mounting.id'))
    printed_by = Column(Integer, ForeignKey('users.id'))
    print_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    lid_id = Column(Integer, ForeignKey('lids.id'), nullable=False)
    seal_id = Column(Integer, ForeignKey('seals.id'), nullable=False)

    material_usages = relationship("MaterialUsage", back_populates="harvest")
    request = relationship("ProductRequest")


class ProductTracking(Base):
    __tablename__ = 'product_tracking'
    id = Column(Integer, primary_key=True)
    harvest_id = Column(Integer, ForeignKey('product_harvest.id'), unique=True, nullable=False)
    sku_id = Column(Integer, ForeignKey('product_skus.id'), nullable=False)
    tracking_id = Column(String(50), unique=True, nullable=False)
    current_status_id = Column(Integer, ForeignKey("product_statuses.id"), nullable=True)
    previous_stage_id = Column(Integer, ForeignKey('lifecycle_stages.id'), nullable=True)
    current_stage_id = Column(Integer, ForeignKey('lifecycle_stages.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('storage_locations.id'), nullable=True)
    last_updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    sku = relationship("ProductSKU", back_populates="trackings")
    stage = relationship('LifecycleStages', foreign_keys=[current_stage_id])
    previous_stage = relationship('LifecycleStages', foreign_keys=[previous_stage_id], backref="previous_stage_products")
    location = relationship('StorageLocation')
    treatment_batch_product = relationship("TreatmentBatchProduct", back_populates="product", uselist=False)
    post_treatment_inspections = relationship("PostTreatmentInspection", back_populates="product")
    quality_controls = relationship("ProductQualityControl", back_populates='product')
    investigation = relationship("ProductInvestigation", back_populates="product", uselist=False)
    status_history = relationship("ProductStatusHistory", back_populates="product")
    quarantine_records = relationship("QuarantinedProducts", back_populates="product")
    current_status = relationship("ProductStatuses", back_populates="products")
    material_usages = relationship("MaterialUsage", back_populates="product")


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


class ProductStatuses(Base):
    __tablename__ = "product_statuses"

    id = Column(Integer, primary_key=True, index=True)
    status_name = Column(String(50), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)

    products = relationship("ProductTracking", back_populates="current_status")
    