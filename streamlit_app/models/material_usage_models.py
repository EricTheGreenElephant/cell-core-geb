from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base


class MaterialUsage(Base):
    __tablename__ = "material_usage"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product_tracking.id"), nullable=False)
    harvest_id = Column(Integer, ForeignKey("product_harvest.id"), nullable=False)
    material_type = Column(String(50), nullable=False)
    lot_number = Column(String(100), nullable=False)
    used_quantity = Column(Numeric(10, 2), nullable=False)
    used_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    used_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(255))

    product = relationship("ProductTracking", back_populates="material_usages")
    harvest = relationship("ProductHarvest", back_populates="material_usages")
    user = relationship("User", back_populates="material_usages")