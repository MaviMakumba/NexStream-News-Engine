from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from src.infrastructure.config.database import Base

class NewsORM(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Yapay Zeka Alanları
    summary = Column(Text, nullable=True)
    sentiment_label = Column(String, nullable=True)
    sentiment_score = Column(Float, nullable=True)