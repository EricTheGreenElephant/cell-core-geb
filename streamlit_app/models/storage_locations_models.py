
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.base import Base


class StorageLocation(Base):
    __tablename__ = 'storage_locations'
    id = Column(Integer, primary_key=True)
    location_name = Column(String)
    location_type = Column(String)
    description = Column(String)

    filaments = relationship("Filament", back_populates="location")