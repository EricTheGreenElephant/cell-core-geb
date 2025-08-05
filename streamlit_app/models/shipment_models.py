from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.base import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_date = Column(DateTime, server_default=func.now())
    ship_date = Column(DateTime)
    delivery_date = Column(DateTime)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    status = Column(String(20), nullable=False, default="Pending")
    tracking_number = Column(String(50))
    carrier = Column(String(5))

    items = relationship("ShipmentItem", back_populates="shipment")


class ShipmentItem(Base):
    __tablename__ = "shipment_items"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product_tracking.id"), nullable=False)
    quantity = Column(Integer, nullable=False)

    shipment = relationship("Shipment", back_populates="items")
    