from src.adapters.analysis.factory import build_analyzer
from src.adapters.analysis.groq_pool import PooledGroqAnalyzer
from src.adapters.analysis.fallback_analyzer import FallbackAnalyzer


def test_build_analyzer_uses_pooled_groq():
    result = build_analyzer()

    assert isinstance(result, FallbackAnalyzer)
    assert isinstance(result.analyzers[0], PooledGroqAnalyzer)
    assert set(result.analyzers[0]._analyzers.keys()) == {"openai/gpt-oss-20b", "qwen/qwen3.8-27b"}
