from sqlalchemy import Column, Integer, String, Text, DateTime, Float
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
    
    # --- YENİ EKLENEN YAPAY ZEKA ALANLARI ---
    summary = Column(Text, nullable=True)       # Haberin yapay zeka özeti
    sentiment_score = Column(Float, nullable=True) # Duygu puanı (-1: Çok Kötü, +1: Çok İyi)
    sentiment_label = Column(String(20), nullable=True) # Etiket (Positive, Negative, Neutral)