from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from app.core.db import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    direction = Column(String(8), nullable=False)  # in | out
    body = Column(Text, nullable=False)
    raw_payload = Column(JSON)
    sent_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    draft_status = Column(String(16), nullable=True)
    send_status = Column(String(16), nullable=True)
    policy_decision = Column(String(16), nullable=True)
    policy_reason = Column(Text)
    prompt_id_used = Column(Integer, ForeignKey("prompts.id"), nullable=True)
    model_used = Column(String(64))
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    confirmed_in_dom_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())