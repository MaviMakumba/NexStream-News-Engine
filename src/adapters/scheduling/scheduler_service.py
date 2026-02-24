import asyncio
import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiokafka import AIOKafkaProducer

# Kafka Ayarları
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
TOPIC_NAME = "news_updates"

async def send_scrape_command():
    """
    Zamanı gelince çalışır ve Kafka'ya 'Haberleri Çek' emri atar.
    """
    print("🚀 GÖREV TETİKLENDİ: Kafka'ya bağlanılıyor...")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    
    try:
        # 1. Bağlantıyı Dene (Timeout ekleyelim ki sonsuza kadar beklemesin)
        await asyncio.wait_for(producer.start(), timeout=10.0)
        
        # 2. Emir Mesajını Hazırla
        command = {
            "source": "BBC Technology",
            "action": "scrape",
            "trigger": "scheduler"
        }
        message = json.dumps(command).encode("utf-8")
        
        # 3. Gönder
        await producer.send_and_wait(TOPIC_NAME, message)
        print(f"✅ ZAMANLAYICI BAŞARILI: '{command['source']}' için emir gönderildi.")
        
    except asyncio.TimeoutError:
        print("❌ ZAMANLAYICI HATASI: Kafka bağlantısı zaman aşımına uğradı (Timeout).")
    except Exception as e:
        print(f"❌ ZAMANLAYICI HATASI: {e}")
    finally:
        # Bağlantıyı temizle
        try:
            await producer.stop()
        except:
            pass

def start_scheduler():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    scheduler = AsyncIOScheduler(event_loop=loop)
    
    # Test için süreyi 1 dakikaya indirelim ki sonucu hızlı görelim
    # misfire_grace_time=60: Eğer sistem kasar ve 60 saniye geç kalırsa bile görevi iptal etme, ÇALIŞTIR.
    scheduler.add_job(send_scrape_command, 'interval', minutes=1, misfire_grace_time=60)
    
    scheduler.start()
    print("⏳ Zamanlayıcı Servisi Başlatıldı (Her 1 dakikada bir deneyecek)...")
    
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    start_scheduler()