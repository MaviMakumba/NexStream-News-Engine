from abc import ABC, abstractmethod
from typing import Optional, Any


class CachePort(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...
