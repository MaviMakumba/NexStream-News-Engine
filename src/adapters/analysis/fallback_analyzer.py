import logging
from typing import List
from src.domain.ports.analysis_port import AnalysisPort, AnalysisError
from src.adapters.analysis.common import neutral_result

logger = logging.getLogger(__name__)


class FallbackAnalyzer(AnalysisPort):
    """Birden çok analyzer'ı sırayla dener; ilk başarılıyı döner.

    Hepsi başarısızsa analyze_text nötr fallback döner (servis hot-path'i asla çökmez).
    """

    def __init__(self, analyzers: List[AnalysisPort]):
        if not analyzers:
            raise ValueError("FallbackAnalyzer en az bir analyzer gerektirir")
        self.analyzers = analyzers

    def analyze_text(self, text: str) -> dict:
        try:
            return self.analyze_or_raise(text)
        except AnalysisError:
            logger.error("Tüm analyzer'lar başarısız, nötr fallback dönülüyor.")
            return neutral_result(text)

    def analyze_or_raise(self, text: str) -> dict:
        for analyzer in self.analyzers:
            try:
                return analyzer.analyze_or_raise(text)
            except AnalysisError as e:
                logger.warning("%s başarısız, sıradaki analyzer'a geçiliyor: %s",
                               type(analyzer).__name__, e)
        raise AnalysisError("Tüm analyzer'lar başarısız")
