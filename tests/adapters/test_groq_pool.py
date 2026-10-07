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


# ── taşma katmanı (7 Eki 2026) ────────────────────────────────────────────────
# Prod: iki birincil model akşamları günlük kotada (TPD) tükeniyor, haberlerin
# ~%13'ü nötr-fallback'e düşüyordu. gpt-oss-120b AYRI bir TPD havuzu ama RAG ile
# paylaşılıyor — bu yüzden yalnız birincillerin HEPSİ soğumadayken kullanılır.

OVERFLOW = "model-overflow"


def _tiered_pool(clock):
    pooled = PooledGroqAnalyzer([A, B], overflow_models=[OVERFLOW], clock=clock, sleep=clock.sleep)
    for analyzer in pooled._analyzers.values():
        analyzer.analyze_or_raise = MagicMock(return_value=OK)
    return pooled


def test_overflow_model_is_not_used_while_a_primary_is_available():
    clock = FakeClock()
    pooled = _tiered_pool(clock)
    record_remaining(OVERFLOW, 8000)  # bütçesi en rahat olsa bile
    record_remaining(A, 100)
    record_remaining(B, 100)

    pooled.analyze_or_raise("x")

    pooled._analyzers[OVERFLOW].analyze_or_raise.assert_not_called()


def test_overflow_model_takes_over_when_all_primaries_are_cooling():
    clock = FakeClock()
    pooled = _tiered_pool(clock)
    pooled._analyzers[A].analyze_or_raise.side_effect = GroqRateLimited(300)
    pooled._analyzers[B].analyze_or_raise.side_effect = GroqRateLimited(300)

    assert pooled.analyze_or_raise("x") == OK
    pooled._analyzers[OVERFLOW].analyze_or_raise.assert_called_once_with("x")
    assert clock.slept == []


def test_primaries_are_preferred_again_once_cooldown_ends():
    clock = FakeClock()
    pooled = _tiered_pool(clock)
    pooled._analyzers[A].analyze_or_raise.side_effect = [GroqRateLimited(100), OK]
    pooled._analyzers[B].analyze_or_raise.side_effect = [GroqRateLimited(100), OK]
    pooled.analyze_or_raise("x")  # overflow devrede

    clock.now += 101
    pooled.analyze_or_raise("y")

    assert pooled._analyzers[OVERFLOW].analyze_or_raise.call_count == 1


def test_waits_only_when_every_model_including_overflow_is_cooling():
    clock = FakeClock()
    pooled = _tiered_pool(clock)
    pooled._analyzers[A].analyze_or_raise.side_effect = [GroqRateLimited(300), OK]
    pooled._analyzers[B].analyze_or_raise.side_effect = [GroqRateLimited(300), OK]
    pooled._analyzers[OVERFLOW].analyze_or_raise.side_effect = [GroqRateLimited(90), OK]

    assert pooled.analyze_or_raise("x") == OK
    assert clock.slept == [pytest.approx(90)]


# ── taşma bütçesi: RAG için ayrılan pay (7 Eki 2026) ──────────────────────────
# 120b'nin TPD'si RAG ile paylaşılıyor. Worker kendi payını bitirince taşma
# modeli devre dışı kalır; kalan kota RAG'a bırakılır (RAG'ın hata vermemesi
# için), haber analizi nötr-fallback'e düşer.

from src.adapters.analysis.token_budget import RollingTokenBudget


def _budgeted_pool(clock, budget):
    pooled = PooledGroqAnalyzer(
        [A, B], overflow_models=[OVERFLOW], overflow_budget=budget,
        clock=clock, sleep=clock.sleep,
    )
    for analyzer in pooled._analyzers.values():
        analyzer.analyze_or_raise = MagicMock(return_value=OK)
    pooled._analyzers[A].analyze_or_raise.side_effect = GroqRateLimited(10_000)
    pooled._analyzers[B].analyze_or_raise.side_effect = GroqRateLimited(10_000)
    return pooled


def test_overflow_model_is_skipped_once_its_budget_is_spent():
    clock = FakeClock()
    budget = RollingTokenBudget(limit=1000, clock=clock)
    budget.record(1000)
    pooled = _budgeted_pool(clock, budget)

    # A/B soğumada, overflow bütçesi dolu -> hiçbir model kalmadı, bekle
    with pytest.raises(AnalysisError):
        pooled.analyze_or_raise("x")
    pooled._analyzers[OVERFLOW].analyze_or_raise.assert_not_called()


def test_overflow_model_is_used_while_budget_has_room():
    clock = FakeClock()
    budget = RollingTokenBudget(limit=1000, clock=clock)
    pooled = _budgeted_pool(clock, budget)

    assert pooled.analyze_or_raise("x") == OK
    pooled._analyzers[OVERFLOW].analyze_or_raise.assert_called_once_with("x")


def test_overflow_usage_feeds_the_budget_but_primary_usage_does_not():
    pooled = PooledGroqAnalyzer(
        [A], overflow_models=[OVERFLOW], overflow_budget=RollingTokenBudget(limit=1000)
    )
    pooled._analyzers[OVERFLOW]._on_usage(300)

    assert pooled._analyzers[A]._on_usage is None
    assert pooled._overflow_budget.used() == 300


def test_waits_for_primary_cooldown_when_overflow_budget_is_spent():
    """Bütçesi dolan taşma modeli 'hemen kullanılabilir' sayılıp beklemeyi
    atlatmamalı — aksi halde haberler soğuma bitmeden nötr-fallback'e düşer."""
    clock = FakeClock()
    budget = RollingTokenBudget(limit=1000, clock=clock)
    budget.record(1000)
    pooled = _budgeted_pool(clock, budget)
    pooled._analyzers[A].analyze_or_raise.side_effect = [GroqRateLimited(300), OK]
    pooled._analyzers[B].analyze_or_raise.side_effect = [GroqRateLimited(120), OK]

    assert pooled.analyze_or_raise("x") == OK
    assert clock.slept == [pytest.approx(120)]
    pooled._analyzers[OVERFLOW].analyze_or_raise.assert_not_called()
