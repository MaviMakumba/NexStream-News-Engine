from sqlalchemy.orm import Session
from src.domain.models.news import NewsORM

class NewsRepository:
    # --- DÜZELTME BURADA ---
    # Artık dışarıdan gelen (Router'dan gelen) db oturumunu kabul ediyor.
    def __init__(self, db: Session):
        self.db = db

    def save_article(self, article_data: dict):
        """
        Haberi veritabanına kaydeder veya günceller.
        """
        # Önce bu URL var mı diye bak (Tekrarı önle)
        existing_news = self.db.query(NewsORM).filter(NewsORM.url == article_data["url"]).first()
        
        if existing_news:
            return existing_news

        news = NewsORM(
            title=article_data["title"],
            source=article_data["source"],
            url=article_data["url"],
            summary=article_data.get("summary"),             # AI Özeti
            sentiment_label=article_data.get("sentiment_label"), # AI Etiketi
            sentiment_score=article_data.get("sentiment_score")  # AI Skoru
        )
        self.db.add(news)
        self.db.commit()
        self.db.refresh(news)
        return news

    def get_latest_news(self, limit: int = 10, sentiment: str = None):
        """
        Son eklenen haberleri getirir. İstenirse duygu durumuna göre filtreler.
        """
        query = self.db.query(NewsORM)
        
        # Eğer filtre varsa (Örn: Sadece 'Positive' olanlar)
        if sentiment:
            query = query.filter(NewsORM.sentiment_label.ilike(f"%{sentiment}%"))
            
        return query.order_by(NewsORM.id.desc()).limit(limit).all()