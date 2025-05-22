from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base


class Lid(Base):
    __tablename__ = 'lids'

    id = Column(Integer, primary_key=True)
    serial_number = Column(String, nullable=False)
    location_id = Column(Integer, ForeignKey('storage_locations.id'))
    qc_result = Column(String, nullable=False)
    received_by = Column(Integer, ForeignKey('users.id'))
    received_at = Column(DateTime, default=datetime.now(timezone.utc))

    location = relationship("StorageLocation")
    receiver = relationship("User")
    