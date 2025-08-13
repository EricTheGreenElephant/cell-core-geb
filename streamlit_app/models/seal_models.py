from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base


class Seal(Base):
    __tablename__ = 'seals'

    id = Column(Integer, primary_key=True)
    serial_number = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    location_id = Column(Integer, ForeignKey('storage_locations.id'))
    qc_result = Column(String, nullable=False)
    received_by = Column(Integer, ForeignKey('users.id'))
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    location = relationship("models.storage_locations_models.StorageLocation")
    seal_receiver = relationship("models.users_models.User", back_populates="received_seals")
    