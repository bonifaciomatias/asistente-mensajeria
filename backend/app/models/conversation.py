from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.core.db import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    channel = Column(String(32), nullable=False)
    status = Column(String(16), default="open")  # open | closed | spam
    summary = Column(Text)
    summary_tokens = Column(Integer, default=0)
    summary_updated_at = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    summary_last_message_id = Column(Integer, nullable=True)