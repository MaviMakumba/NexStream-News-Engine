"""Kayan pencereli token bütçesi — paylaşılan bir Groq modelinde worker'ın
kendi payını aşmasını önler (kalan kota başka tüketiciye, ör. RAG'a kalır).

Groq TPD'si de kayan bir 24 saatlik pencere (bkz. groq_analyzer.py), bu yüzden
günlük sıfırlanan bir sayaç değil kayan pencere kullanılır. Süreç içi tutulur:
worker yeniden başlayınca sayaç sıfırlanır — bu yalnız deploy anında olur ve
en kötü durumda bütçe bir kez daha harcanabilir.
"""
import threading
import time
from collections import deque


class RollingTokenBudget:
    def __init__(self, limit: int, window_seconds: float = 86400.0, clock=time.monotonic):
        self.limit = limit
        self._window = window_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._events: deque[tuple[float, int]] = deque()

    def record(self, tokens: int) -> None:
        with self._lock:
            self._events.append((self._clock(), tokens))

    def used(self) -> int:
        with self._lock:
            self._expire()
            return sum(t for _, t in self._events)

    def has_room(self) -> bool:
        return self.used() < self.limit

    def _expire(self) -> None:
        cutoff = self._clock() - self._window
        while self._events and self._events[0][0] <= cutoff:
            self._events.popleft()
