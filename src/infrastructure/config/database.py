import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# .env dosyasındaki gizli bilgileri Python'a yüklüyoruz
load_dotenv()

# Bağlantı adresini oluşturuyoruz (PostgreSQL formatı)
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Engine: Veritabanı ile iletişim kuran ana motorumuz.
engine = create_engine(DATABASE_URL)

# SessionLocal: Veritabanı üzerinde işlem (okuma/yazma) yapacağımız oturumlar.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: ORM modellerimizin miras alacağı ana sınıf. Tablolar bu sınıf üzerinden türetilecek.
Base = declarative_base()

# --- İŞTE EKSİK OLAN SİHİRLİ FONKSİYON BU ---
def get_db():
    """
    Her istek (request) geldiğinde yeni bir veritabanı oturumu açar,
    iş bitince kapatır.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()