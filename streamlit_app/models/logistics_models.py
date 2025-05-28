from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from db.base import Base


class TreatmentBatch(Base):
    __tablename__ = 'treatment_batches'

    id = Column(Integer, primary_key=True)
    sent_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    sent_at = Column(DateTime, server_default=func.now())
    received_at = Column(DateTime)
    notes = Column(String)
    status = Column(String, default='Shipped', nullable=False)

    products = relationship("TreatmentBatchProduct", back_populates="batch")


class TreatmentBatchProduct(Base):
    __tablename__ = 'treatment_batch_products'

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('treatment_batches.id'))
    product_id = Column(Integer, ForeignKey('product_tracking.id'), unique=True)
    surface_treat = Column(Boolean, nullable=False)
    sterilize = Column(Boolean, nullable=False)

    batch = relationship("TreatmentBatch", back_populates="products")