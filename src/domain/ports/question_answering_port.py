"""src/domain/ports/question_answering_port.py

RAG soru-cevap port'u — kanıt paketinden (retrieval sonuçları + tam Article
metadata'sı) yapılandırılmış bir sentez üretir. AnalysisPort'a metot
EKLENMEDİ: proje zaten aynı gerekçeyle QueryExpansionPort'u AnalysisPort'tan
ayrı tutmuş (ikisi de Groq kullanır ama farklı sorumluluklar, ISP ihlali
riski). Somut implementasyon: GroqQuestionAnswerer.
"""

from abc import ABC, abstractmethod


class QuestionAnsweringError(Exception):
    """Groq çağrısı tamamen başarısız olduğunda fırlatılır. AnalysisPort'un
    aksine SESSİZ NÖTR FALLBACK YOK — bir soruya 'kibarca uydurulmuş' bir
    cevap vermek, açık bir hata vermekten daha kötü (kullanıcı yanlış
    bilgiye güvenebilir)."""


class QuestionAnsweringPort(ABC):
    @abstractmethod
    def answer(
        self,
        question: str,
        sources: list,
        history: list,
        corroboration_level: str,
    ) -> dict:
        """Dönüş: {"coverage": "full"|"partial"|"none", "answer": str,
        "used_sources": list[int]}. Başarısızlıkta QuestionAnsweringError
        fırlatır (fail-open DEĞİL, fail-loud)."""
        ...
