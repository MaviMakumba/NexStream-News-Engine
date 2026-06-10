"""Newsletter abonesi repository port'u — kayıt/tercih/deaktivasyon sözleşmesi.

Somut implementasyon: adapters/repositories/subscriber_repository.py (PostgreSQL).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models.subscriber import Subscriber


class SubscriberRepositoryPort(ABC):
    @abstractmethod
    def save_subscriber(self, subscriber: Subscriber) -> Subscriber: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Subscriber]: ...

    @abstractmethod
    def get_active_subscribers(self) -> List[Subscriber]: ...

    @abstractmethod
    def get_instant_subscribers_for_keyword(self, keyword: str) -> List[Subscriber]: ...

    @abstractmethod
    def update_subscriber(self, subscriber: Subscriber) -> bool: ...

    @abstractmethod
    def deactivate(self, email: str) -> bool: ...
