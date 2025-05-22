from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base


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
    requested_at = Column(DateTime, default=datetime.now(timezone.utc))
    notes = Column(String)

    product = relationship("ProductType")


class ProductHarvest(Base):
    __tablename__ = 'product_harvest'
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('product_requests.id'))
    filament_mounting_id = Column(Integer, ForeignKey('filament_mounting.id'))
    printed_by = Column(Integer, ForeignKey('users.id'))
    print_date = Column(DateTime, default=datetime.now(timezone.utc))
    print_status = Column(String)
    lid_id = Column(Integer, ForeignKey('lids.id'))


class ProductTracking(Base):
    __tablename__ = 'product_tracking'
    id = Column(Integer, primary_key=True)
    harvest_id = Column(Integer, ForeignKey('product_harvest.id'))
    current_status = Column(String)
    last_updated_at = Column(DateTime, default=datetime.now(timezone.utc))