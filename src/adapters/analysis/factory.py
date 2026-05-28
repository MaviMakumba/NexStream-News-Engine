"""Analyzer kompozisyon noktası — Groq birincil, HuggingFace opsiyonel yedek."""
from src.adapters.analysis.groq_analyzer import GroqAnalyzer
from src.adapters.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from src.adapters.analysis.fallback_analyzer import FallbackAnalyzer
from src.domain.ports.analysis_port import AnalysisPort
from src.infrastructure.config.settings import settings


def build_analyzer() -> AnalysisPort:
    analyzers = [GroqAnalyzer()]
    if settings.huggingface_api_key:
        analyzers.append(HuggingFaceAnalyzer())
    return FallbackAnalyzer(analyzers)
