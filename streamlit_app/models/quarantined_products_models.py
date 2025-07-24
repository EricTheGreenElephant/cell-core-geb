from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.base import Base
from datetime import datetime, timezone


class QuarantinedProducts(Base):
    __tablename__ = "quarantined_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_tracking.id"), nullable=False)
    from_stage_id = Column(Integer, ForeignKey("lifecycle_stages.id"), nullable=False)
    source = Column(String(50), nullable=False)
    location_id = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    quarantine_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    quarantined_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    quarantine_reason = Column(String(255), nullable=True)
    quarantine_status = Column(String(20), nullable=False, default="Active")
    result = Column(String(20), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    product = relationship("ProductTracking", back_populates="quarantine_records")
    from_stage = relationship("LifecycleStages", back_populates="quarantined_products")
    location = relationship("StorageLocation", back_populates="quarantined_products")
    quarantined_user = relationship("User", foreign_keys=[quarantined_by], back_populates="quarantines_created")
    resolved_user = relationship("User", foreign_keys=[resolved_by], back_populates="quarantines_resolved")
