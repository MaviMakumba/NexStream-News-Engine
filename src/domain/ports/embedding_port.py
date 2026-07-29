"""Embedding port'u — metni vektöre çeviren bileşen sözleşmesi.

İki somut implementasyon var (seçimi `adapters/search/embedder_factory.py` yapar):
- `HttpEmbedderAdapter` — varsayılan; modeli ayrı bir serviste tutar, RAM'de tek kopya
- `SentenceTransformerEmbedder` — modeli süreç içine yükler, Docker'sız geliştirme için
"""

from abc import ABC, abstractmethod


class EmbeddingPort(ABC):

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass
