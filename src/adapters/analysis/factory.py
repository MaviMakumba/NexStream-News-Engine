"""Analyzer + sorgu genişletme kompozisyon noktası — Groq birincil, HuggingFace opsiyonel yedek."""
from typing import Optional
from src.adapters.analysis.groq_analyzer import GroqAnalyzer
from src.adapters.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from src.adapters.analysis.fallback_analyzer import FallbackAnalyzer
from src.adapters.analysis.groq_query_expander import GroqQueryExpander
from src.adapters.analysis.caching_query_expander import CachingQueryExpander
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.domain.ports.cache_port import CachePort
from src.infrastructure.config.settings import settings


def build_analyzer() -> AnalysisPort:
    analyzers = [GroqAnalyzer()]
    if settings.huggingface_api_key:
        analyzers.append(HuggingFaceAnalyzer())
    return FallbackAnalyzer(analyzers)


def build_query_expander(cache: CachePort) -> Optional[QueryExpansionPort]:
    """Sorgu genişletme kompozisyon noktası. `cache` dışarıdan verilir —
    dependencies.py'deki tekil CachePort singleton'ı paylaşılsın diye
    (kendi cache'ini yaratırsa tekillik bozulur)."""
    if not settings.search_query_expansion_enabled:
        return None
    return CachingQueryExpander(GroqQueryExpander(), cache)
