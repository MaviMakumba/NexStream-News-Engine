import asyncio
import json
from aiokafka import AIOKafkaConsumer
from src.adapters.repositories.news_repository import NewsRepository
from src.application.services.news_service import NewsService
from src.adapters.scrapers.bbc_scraper import BBCRssScraper

async def consume():
    # 1. Altyapıyı Hazırla (Dependency Injection)
    # İşçi, işini yapabilmek için depoya, servise ve robota ihtiyaç duyar.
    repo = NewsRepository()
    service = NewsService(repo)
    bbc_scraper = BBCRssScraper()

    # 2. Kafka Tüketicisini (Consumer) Başlat
    consumer = AIOKafkaConsumer(
        'news_updates', # Dinlenecek konu başlığı
        bootstrap_servers='kafka:29092',
        group_id="news_workers_group" # Aynı işi yapan işçi grubu
    )
    
    # --- RETRY MEKANİZMASI BAŞLANGICI ---
    print("⏳ Kafka'ya bağlanmaya çalışılıyor...")
    while True:
        try:
            await consumer.start()
            print("✅ Kafka Bağlantısı Başarılı!")
            break # Bağlandıysak döngüden çık
        except Exception as e:
            print(f"⚠️ Kafka henüz hazır değil, 5 saniye sonra tekrar denenecek... ({e})")
            await asyncio.sleep(5)
    # --- RETRY MEKANİZMASI BİTİŞİ ---

    print("👷‍♂️ Kafka Worker (İşçi) işbaşı yaptı! Mesaj bekleniyor...")

    try:
        # 3. Sonsuz Döngüde Mesaj Bekle
        async for msg in consumer:
            print(f"📨 Mesaj Yakalandı: {msg.value}")
            
            # Gelen mesajı JSON'a çevir
            data = json.loads(msg.value)
            
            # Mesajın içeriğine bakıp işi yap
            if data.get("source") == "BBC Technology":
                print("⚙️ BBC Güncellemesi Başlatılıyor...")
                # Haberleri çek ve kaydet (Senkron kodu burada çağırıyoruz)
                # Not: Gerçek projede bunu thread pool ile yapmak daha doğrudur
                service.update_news_from_source(bbc_scraper)
                print("✅ İşlem Tamamlandı. Sıradaki gelsin!")

    except Exception as e:
        print(f"❌ İşçi Hatası: {e}")
    finally:
        await consumer.stop()
        repo.close()

if __name__ == "__main__":
    # Asenkron döngüyü başlat
    asyncio.run(consume())