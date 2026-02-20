from src.infrastructure.config.database import engine, Base
# Tablo modelimizi import etmezsek SQLAlchemy tablonun varlığından haberdar olmaz
from src.adapters.repositories.orm_models import NewsORM

def create_tables():
    print("Veritabanı tabloları oluşturuluyor...")
    # Base.metadata.create_all komutu, Base sınıfından türeyen tüm modelleri bulup veritabanında oluşturur.
    Base.metadata.create_all(bind=engine)
    print("İşlem başarılı! Tablolar hazır.")

if __name__ == "__main__":
    create_tables()