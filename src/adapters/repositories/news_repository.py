from sqlalchemy.orm import Session
from src.adapters.repositories.orm_models import NewsORM
from src.infrastructure.config.database import SessionLocal

class NewsRepository:
    def __init__(self):
        # Her depo işleminin kendi veritabanı oturumu olur
        self.db: Session = SessionLocal()

    def save_article(self, article_data: dict) -> bool:
        """
        Haberi veritabanına kaydeder.
        Eğer haberin linki (url) zaten varsa kaydetmez (Duplicate Prevention).
        """
        try:
            # 1. Kontrol Et: Bu linkte bir haber zaten var mı?
            existing_news = self.db.query(NewsORM).filter(NewsORM.url == article_data["url"]).first()
            
            if existing_news:
                # Haber zaten var, pas geçiyoruz
                print(f"⚠️ Zaten kayıtlı: {article_data['title'][:30]}...")
                return False

            # 2. Yoksa Yeni Kayıt Oluştur (Mapping: Dict -> ORM Nesnesi)
            new_news = NewsORM(
                title=article_data["title"],
                content=article_data["content"],
                source=article_data["source"],
                url=article_data["url"]
            )
            
            # 3. Veritabanına Gönder ve Onayla (Commit)
            self.db.add(new_news)
            self.db.commit()
            print(f"💾 Kaydedildi: {article_data['title'][:30]}...")
            return True
            
        except Exception as e:
            print(f"❌ Veritabanı Hatası: {e}")
            self.db.rollback() # Hata olursa işlemi geri al
            return False
            
    def close(self):
        self.db.close()