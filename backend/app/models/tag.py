from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.core.db import Base

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    color = Column(String(16))
    created_at = Column(DateTime, server_default=func.now())

class ContactTag(Base):
    __tablename__ = "contact_tags"
    contact_id = Column(Integer, ForeignKey("contacts.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)