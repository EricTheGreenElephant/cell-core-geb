from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(String(255), nullable=False)
    changed_by = Column(Integer, nullable=False)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)