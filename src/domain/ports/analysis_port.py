"""LLM analiz port'u — sentiment + NER + topic çıkarımı sözleşmesi.

Somut implementasyonlar: GroqAnalyzer (birincil), HuggingFaceAnalyzer (yedek),
FallbackAnalyzer (zincir). `analyze_text` asla fırlatmaz; `analyze_or_raise`
fallback zincirinin "bu analyzer başarısız, sıradakine geç" sinyalidir.
"""

from abc import ABC, abstractmethod


class AnalysisError(Exception):
    """Bir analyzer analizi tamamlayamadığında fırlatılır (fallback zinciri için sinyal)."""


class AnalysisPort(ABC):
    """Yapay Zeka analizi için sözleşme. Yarın TextBlob gider, Gemini gelir, kod değişmez."""

    @abstractmethod
    def analyze_text(self, text: str) -> dict:
        """
        Dönüş formatı garanti edilmelidir:
        {'sentiment_score': float, 'sentiment_label': str, 'summary': str,
         'entities': dict, 'topic': str}
        Başarısızlıkta exception fırlatmaz — nötr fallback döner.
        """
        pass

    def analyze_or_raise(self, text: str) -> dict:
        """analyze_text'in fallback zincirinde kullanılan, başarısızlıkta AnalysisError
        fırlatan sürümü. Varsayılan güvenli sürüme delege eder; resilient analyzer'lar override eder."""
        return self.analyze_text(text)
