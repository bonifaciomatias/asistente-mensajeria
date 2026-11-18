from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from app.core.db import Base

class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True)
    stage = Column(String(64), nullable=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=True)
    intent = Column(String(64), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    system_prompt = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())