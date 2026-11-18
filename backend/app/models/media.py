from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.db import Base

class MediaItem(Base):
    __tablename__ = "media_catalog"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    mime_type = Column(String(128))
    description = Column(Text)
    tags = Column(Text)
    created_at = Column(DateTime, server_default=func.now())