
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.base import Base


class StorageLocation(Base):
    __tablename__ = 'storage_locations'
    id = Column(Integer, primary_key=True)
    location_name = Column(String)
    location_type = Column(String)
    description = Column(String)

    filaments = relationship("models.filament_models.Filament", back_populates="location")
    product_tracking = relationship("models.production_models.ProductTracking", back_populates="location")
    lids = relationship("models.lid_models.Lid", back_populates="location")
    quarantined_products = relationship("QuarantinedProducts", back_populates="location")