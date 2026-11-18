from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.core.db import Base

class PolicyLog(Base):
    __tablename__ = "policy_log"
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    decision = Column(String(16), nullable=False)  # auto_send | escalate | silence
    rule_applied = Column(String(128), nullable=False)
    reason = Column(Text)
    evaluated_at = Column(DateTime, server_default=func.now())

class RateState(Base):
    __tablename__ = "rate_state"
    id = Column(Integer, primary_key=True)
    scope = Column(String(16), nullable=False)  # global | contact
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    window_kind = Column(String(8), nullable=False)  # hour | day
    window_start = Column(DateTime, nullable=False)
    count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class HumanOverride(Base):
    __tablename__ = "human_overrides"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    activated_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)
    reason = Column(Text)
    active = Column(Integer, default=1)  # 1 | 0 (SQLite-friendly)