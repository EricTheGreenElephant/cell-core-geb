from sqlalchemy import Column, Integer, ForeignKey, DateTime, DECIMAL, String, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base


class ProductQualityControl(Base):
    __tablename__ = 'product_quality_control'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('product_tracking.id'), nullable=False)
    inspected_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    inspected_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    weight_grams = Column(DECIMAL(6, 2), nullable=False)
    pressure_drop = Column(DECIMAL(6, 3), nullable=False)
    visual_pass = Column(Boolean, nullable=False)
    inspection_result = Column(String(20), nullable=False)
    notes = Column(String(255))

    product = relationship('models.production_models.ProductTracking', back_populates='quality_controls')
    inspector = relationship('models.users_models.User', backref='inspected_products')


class PostTreatmentInspection(Base):
    __tablename__ = "post_treatment_inspections"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product_tracking.id"), nullable=False)
    inspected_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    inspected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    visual_pass = Column(Boolean, nullable=False)
    surface_treated = Column(Boolean, nullable=False)
    sterilized = Column(Boolean, nullable=False)
    qc_result = Column(String(20), nullable=False)
    notes = Column(String(255), nullable=True)

    product = relationship("ProductTracking", back_populates="post_treatment_inspections")
    inspector = relationship("User", back_populates="post_treatment_inspections")