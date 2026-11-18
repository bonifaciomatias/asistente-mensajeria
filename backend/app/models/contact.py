from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.db import Base

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(255), nullable=False, index=True)
    channel = Column(String(32), nullable=False)  # telegram | messenger
    display_name = Column(String(255))
    stage = Column(String(64), default="nuevo")
    notes = Column(Text)
    human_override_until = Column(DateTime, nullable=True)
    first_seen_at = Column(DateTime, server_default=func.now())
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Un contacto por (canal, external_id)
        {"sqlite_autoincrement": True},
    )