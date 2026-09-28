from unittest.mock import MagicMock
from src.adapters.analysis import groq_pool
from src.adapters.analysis.groq_pool import PooledGroqAnalyzer, pick_least_loaded, record_remaining


def setup_function(_):
    # Modül seviyesi paylaşılan durum testler arasında sızmasın diye sıfırla.
    groq_pool._remaining_tokens.clear()
    groq_pool._cooldown_until.clear()


def test_pick_least_loaded_prefers_higher_remaining():
    record_remaining("model-a", 500)
    record_remaining("model-b", 7000)
    assert pick_least_loaded(["model-a", "model-b"]) == "model-b"


def test_pick_least_loaded_prefers_never_called_model():
    record_remaining("model-a", 500)
    # "model-b" hiç çağrılmadı -> tam bütçeli sayılır, önce o denenir
    assert pick_least_loaded(["model-a", "model-b"]) == "model-b"


def test_pooled_analyzer_delegates_to_least_loaded_model():
    record_remaining("openai/gpt-oss-20b", 100)
    record_remaining("qwen/qwen3.8-27b", 7000)

    pooled = PooledGroqAnalyzer(["openai/gpt-oss-20b", "qwen/qwen3.8-27b"])
    mock_result = {"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "ok", "entities": {}, "topic": "Other"}
    for analyzer in pooled._analyzers.values():
        analyzer.analyze_or_raise = MagicMock(return_value=mock_result)

    result = pooled.analyze_text("test content")

    pooled._analyzers["qwen/qwen3.8-27b"].analyze_or_raise.assert_called_once_with("test content")
    pooled._analyzers["openai/gpt-oss-20b"].analyze_or_raise.assert_not_called()
    assert result == mock_result


def test_record_remaining_is_thread_safe_under_concurrent_writes():
    import threading

    def writer(model, value):
        for _ in range(100):
            record_remaining(model, value)

    threads = [threading.Thread(target=writer, args=(f"model-{i}", i)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for i in range(10):
        assert groq_pool._remaining_tokens[f"model-{i}"] == i


# ── 429 failover (28 Eyl 2026) ────────────────────────────────────────────────
# Prod: havuz TPM'e göre seçiyordu, bağlayıcı limit ise TPD'ydi; 20b 429
# alınca aynı modelde ~200 sn uyunuyordu (24 saatte 20b 248K token, qwen 1.3K).
# Artık 429 alan model Retry-After kadar "soğumaya" alınır, istek hemen
# havuzdaki diğer modele gider.

import pytest
from src.adapters.analysis.groq_analyzer import GroqRateLimited
from src.domain.ports.analysis_port import AnalysisError

A, B = "model-a", "model-b"
OK = {"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "ok", "entities": {}, "topic": "Other"}


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def _pool(clock):
    pooled = PooledGroqAnalyzer([A, B], clock=clock, sleep=clock.sleep)
    for analyzer in pooled._analyzers.values():
        analyzer.analyze_or_raise = MagicMock(return_value=OK)
    return pooled


def test_pool_builds_analyzers_that_do_not_sleep_on_rate_limit():
    pooled = PooledGroqAnalyzer([A, B])
    assert all(a.wait_on_rate_limit is False for a in pooled._analyzers.values())


def test_rate_limited_model_fails_over_to_other_model_immediately():
    clock = FakeClock()
    pooled = _pool(clock)
    record_remaining(B, 100)  # A seçilsin
    pooled._analyzers[A].analyze_or_raise.side_effect = GroqRateLimited(200)

    assert pooled.analyze_or_raise("x") == OK
    pooled._analyzers[B].analyze_or_raise.assert_called_once_with("x")
    assert clock.slept == []


def test_cooling_model_is_skipped_on_following_calls():
    clock = FakeClock()
    pooled = _pool(clock)
    record_remaining(B, 100)
    pooled._analyzers[A].analyze_or_raise.side_effect = GroqRateLimited(200)
    pooled.analyze_or_raise("x")
    pooled._analyzers[A].analyze_or_raise.reset_mock()

    clock.now += 50  # hâlâ soğumada
    pooled.analyze_or_raise("y")
    pooled._analyzers[A].analyze_or_raise.assert_not_called()


def test_model_becomes_eligible_again_after_cooldown():
    clock = FakeClock()
    pooled = _pool(clock)
    record_remaining(B, 100)
    pooled._analyzers[A].analyze_or_raise.side_effect = [GroqRateLimited(200), OK]
    pooled.analyze_or_raise("x")

    clock.now += 201
    pooled.analyze_or_raise("y")
    assert pooled._analyzers[A].analyze_or_raise.call_count == 2


def test_waits_for_earliest_cooldown_when_all_models_cooling():
    clock = FakeClock()
    pooled = _pool(clock)
    pooled._analyzers[A].analyze_or_raise.side_effect = [GroqRateLimited(300), OK]
    pooled._analyzers[B].analyze_or_raise.side_effect = [GroqRateLimited(120), OK]

    assert pooled.analyze_or_raise("x") == OK
    assert clock.slept == [pytest.approx(120)]


def test_non_rate_limit_failure_propagates_for_fallback_chain():
    """analyze_or_raise override edilmediği için Groq hatası yutulup nötr sonuç
    dönüyordu — FallbackAnalyzer'daki HuggingFace yedeği hiç tetiklenemiyordu."""
    clock = FakeClock()
    pooled = _pool(clock)
    for analyzer in pooled._analyzers.values():
        analyzer.analyze_or_raise.side_effect = AnalysisError("boom")

    with pytest.raises(AnalysisError):
        pooled.analyze_or_raise("x")
    assert pooled.analyze_text("x")["sentiment_label"] == "Neutral"


def test_gives_up_after_bounded_attempts_when_limits_never_clear():
    clock = FakeClock()
    pooled = _pool(clock)
    for analyzer in pooled._analyzers.values():
        analyzer.analyze_or_raise.side_effect = GroqRateLimited(60)

    with pytest.raises(AnalysisError):
        pooled.analyze_or_raise("x")
    assert len(clock.slept) < 10
