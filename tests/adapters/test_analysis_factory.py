from src.adapters.analysis.factory import build_analyzer
from src.adapters.analysis.groq_pool import PooledGroqAnalyzer
from src.adapters.analysis.fallback_analyzer import FallbackAnalyzer


def test_build_analyzer_uses_pooled_groq():
    result = build_analyzer()

    assert isinstance(result, FallbackAnalyzer)
    assert isinstance(result.analyzers[0], PooledGroqAnalyzer)
    assert result.analyzers[0]._primary == ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]


def test_build_analyzer_registers_gpt_oss_120b_as_overflow_tier():
    pooled = build_analyzer().analyzers[0]

    assert "openai/gpt-oss-120b" in pooled._analyzers
    assert pooled._overflow == ["openai/gpt-oss-120b"]
    assert pooled._primary == ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]


def test_overflow_budget_leaves_room_for_rag(monkeypatch):
    from src.infrastructure.config.settings import settings
    monkeypatch.setattr(settings, "groq_overflow_daily_token_budget", 123_000)

    pooled = build_analyzer().analyzers[0]

    assert pooled._overflow_budget.limit == 123_000
