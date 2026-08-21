"""Sorgu genişletme port'u — arama sorgusuna ilişkili ek terimler üretir
("İstanbul" → "Beykoz", "futbol" → "Beşiktaş" gibi). Somut implementasyon:
GroqQueryExpander (+ CachingQueryExpander decorator).
"""

from abc import ABC, abstractmethod
from typing import List


class QueryExpansionPort(ABC):
    @abstractmethod
    def expand(self, query: str) -> List[str]: ...
