"""ArticleTextPort — bir haber URL'sinden temiz makale metni getirme sözleşmesi.

`NewsScraperPort` (RSS listesi) ile KARIŞTIRILMAMALI: o haber LİSTESİ üretir, bu tek bir
haberin gövde metnini soru anında getirir (RAG, spec 2026-10-07-rag-tam-metin-design.md).
"""

from abc import ABC, abstractmethod
from typing import Optional


class ArticleTextPort(ABC):
    @abstractmethod
    def fetch(self, url: str) -> Optional[str]:
        """Makale gövde metnini döner; paywall/engel/timeout/boş sonuç dahil HER başarısızlıkta
        `None`. ASLA exception fırlatmaz (çağıran fail-open'dır)."""
