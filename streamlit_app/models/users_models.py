from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.base import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    display_name = Column(String)

    received_filaments = relationship("Filament", back_populates="received_user")
    mounted_filaments = relationship("FilamentMounting", back_populates="mounted_by_user", foreign_keys='FilamentMounting.mounted_by')
    unmounted_filaments = relationship("FilamentMounting", back_populates="unmounted_by_user", foreign_keys='FilamentMounting.unmounted_by')

