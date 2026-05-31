from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.models.user import User, UserSession


class UserRepositoryPort(ABC):
    @abstractmethod
    def create_user(self, user: User) -> User: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def update_tier(self, user_id: int, tier: str, stripe_customer_id: Optional[str] = None) -> bool: ...

    @abstractmethod
    def create_session(self, session: UserSession) -> UserSession: ...

    @abstractmethod
    def get_session(self, token: str) -> Optional[UserSession]: ...

    @abstractmethod
    def delete_session(self, token: str) -> bool: ...

    @abstractmethod
    def log_usage(self, user_id: Optional[int], endpoint: str, method: str, status_code: int, response_ms: float) -> None: ...

    @abstractmethod
    def get_usage_stats(self, user_id: Optional[int], days: int) -> List[dict]: ...

    @abstractmethod
    def get_daily_usage_count(self, user_id: int) -> int: ...
