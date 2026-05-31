import asyncio
import json
import logging
from aiokafka import AIOKafkaProducer
from src.domain.ports.messaging_port import MessagePublisherPort

logger = logging.getLogger(__name__)


class KafkaPublisherAdapter(MessagePublisherPort):
    def __init__(self, bootstrap_servers: str):
        self._bootstrap_servers = bootstrap_servers
        self.producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def start(self, retries: int = 30, delay: float = 3.0):
        """Kafka hazır olana kadar yeniden dener — broker geç açılırsa servis çökmez.

        Başarısız her denemede producer yeniden oluşturulur; aiokafka başarısız
        bir start() sonrası aynı producer'ı tekrar kullanmaya izin vermez.
        """
        for attempt in range(1, retries + 1):
            try:
                await self.producer.start()
                if attempt > 1:
                    logger.info("Kafka'ya bağlanıldı (deneme %d).", attempt)
                return
            except Exception as e:
                logger.warning(
                    "Kafka'ya bağlanılamadı (deneme %d/%d): %s", attempt, retries, e
                )
                try:
                    await self.producer.stop()
                except Exception:
                    pass
                self.producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap_servers)
                if attempt < retries:
                    await asyncio.sleep(delay)
        raise RuntimeError(f"Kafka'ya {retries} denemede bağlanılamadı: {self._bootstrap_servers}")

    async def stop(self):
        await self.producer.stop()

    async def publish(self, topic: str, message: dict) -> bool:
        try:
            message_bytes = json.dumps(message).encode("utf-8")
            await self.producer.send_and_wait(topic, message_bytes)
            return True
        except Exception as e:
            logger.error("Kafka yayın hatası: %s", e)
            return False
