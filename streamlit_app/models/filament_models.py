from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Computed
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.base import Base


class Filament(Base):
    __tablename__ = 'filaments'
    id = Column(Integer, primary_key=True)
    serial_number = Column(String, nullable=False)
    weight_grams = Column(Float, nullable=False)
    location_id = Column(Integer, ForeignKey('storage_locations.id'))
    qc_result = Column(String)
    received_by = Column(Integer, ForeignKey('users.id'))
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    received_user = relationship("models.users_models.User", back_populates="received_filaments")
    location = relationship("models.storage_locations_models.StorageLocation", back_populates="filaments")
    mountings = relationship("models.filament_models.FilamentMounting", back_populates="filament")
    acclimatizations = relationship("models.filament_models.FilamentAcclimatization", back_populates="filament")


class FilamentMounting(Base):
    __tablename__ = 'filament_mounting'
    id = Column(Integer, primary_key=True)
    filament_id = Column(Integer, ForeignKey('filaments.id'))
    printer_id = Column(Integer, ForeignKey('printers.id'))
    mounted_by = Column(Integer, ForeignKey('users.id'))
    remaining_weight = Column(Float)
    mounted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    unmounted_at = Column(DateTime, nullable=True)
    unmounted_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    status = Column(String, nullable=False, default='In Use')

    filament = relationship("models.filament_models.Filament", back_populates="mountings")
    printer = relationship("models.printers_models.Printer", back_populates="mountings")
    mounted_by_user = relationship("models.users_models.User", back_populates="mounted_filaments", foreign_keys=[mounted_by])
    unmounted_by_user = relationship("models.users_models.User", back_populates="unmounted_filaments", foreign_keys=[unmounted_by])


class FilamentAcclimatization(Base):
    __tablename__ = 'filament_acclimatization'
    id = Column(Integer, primary_key=True)
    filament_id = Column(Integer, ForeignKey('filaments.id'))
    status = Column(String)
    moved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    moved_by = Column(Integer, ForeignKey('users.id'))
    ready_at = Column(DateTime, Computed("DATEADD(DAY, 2, moved_at)", persisted=True))

    filament = relationship("models.filament_models.Filament", back_populates="acclimatizations")