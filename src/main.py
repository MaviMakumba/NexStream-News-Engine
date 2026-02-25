import uvicorn
from fastapi import FastAPI
from src.infrastructure.config.database import engine, Base

# Router'ımızı içeri alıyoruz
from src.adapters.api.routers import news_router

# Veritabanı tablolarını oluştur (Eğer yoksa)
Base.metadata.create_all(bind=engine)

# FastAPI Uygulamasını Başlat
app = FastAPI(
    title="NexStream News Engine API",
    description="Yapay Zeka Destekli Haber Motoru",
    version="1.0.0"
)

# --- ROUTER BAĞLANTISI (PROFESYONEL DOKUNUŞ) ---
# Artık tüm haber işlemleri news_router içinde yönetiliyor.
# Ana dosyamız tertemiz kaldı.
app.include_router(news_router.router)

@app.get("/")
def root():
    return {"message": "NexStream API Çalışıyor! Haberler için /news adresine gidin."}

if __name__ == "__main__":
    # Uygulamayı 0.0.0.0 adresinden (dışarıya açık) çalıştır
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)