from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base


class ProductInvestigation(Base):
    __tablename__ = "product_investigations"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product_tracking.id"), nullable=False)
    status = Column(String(50), nullable=False, default="Under Investigation")
    deviation_number = Column(String(100), nullable=False)
    comment = Column(String(255), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("ProductTracking", back_populates="investigation")
    created_user = relationship("User", back_populates="investigations_created")
    