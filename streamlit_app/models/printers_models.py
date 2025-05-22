
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.base import Base


class Printer(Base):
    __tablename__ = 'printers'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(String)

    mountings = relationship("FilamentMounting", back_populates="printer")