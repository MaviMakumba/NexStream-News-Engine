import json
from aiokafka import AIOKafkaProducer
from src.domain.ports.messaging_port import MessagePublisherPort

class KafkaPublisherAdapter(MessagePublisherPort):
    """
    MessagePublisherPort sözleşmesini imzalayan Kafka İşçisi.
    """
    def __init__(self, bootstrap_servers: str):
        self.producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def publish(self, topic: str, message: dict) -> bool:
        try:
            # Mesajı JSON'a çevirip Kafka'ya fırlatıyoruz
            message_bytes = json.dumps(message).encode("utf-8")
            await self.producer.send_and_wait(topic, message_bytes)
            return True
        except Exception as e:
            print(f"❌ Kafka Yayın Hatası: {e}")
            return False