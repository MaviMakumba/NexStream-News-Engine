from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from src.infrastructure.config.database import Base

class NewsORM(Base):
    __tablename__ = "news_articles"

    # Sütunlarımızı tanımlıyoruz
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False) # Haber başlığı, boş olamaz
    content = Column(Text, nullable=False)      # Haberin içeriği
    source = Column(String(50), nullable=False) # Haberin kaynağı (Örn: CNN, Twitter)
    url = Column(String, unique=True)           # Haberin linki (Aynı haberi 2 kez kaydetmemek için unique)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # Kayıt zamanı