from abc import ABC, abstractmethod

class MessagePublisherPort(ABC):
    """Bir mesaj yayınlayabilen bir şey var. RabbitMQ, Kafka, AWS SNS... Ne olursa olsun bu kurallara uyacak."""
    @abstractmethod
    async def publish(self, topic: str, message: dict) -> bool:
        pass