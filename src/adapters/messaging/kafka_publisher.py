import json
import logging
from aiokafka import AIOKafkaProducer
from src.domain.ports.messaging_port import MessagePublisherPort

logger = logging.getLogger(__name__)


class KafkaPublisherAdapter(MessagePublisherPort):
    def __init__(self, bootstrap_servers: str):
        self.producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def start(self):
        await self.producer.start()

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