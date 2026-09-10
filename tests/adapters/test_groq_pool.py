from unittest.mock import MagicMock
from src.adapters.analysis import groq_pool
from src.adapters.analysis.groq_pool import PooledGroqAnalyzer, pick_least_loaded, record_remaining


def setup_function(_):
    # Modül seviyesi paylaşılan durum testler arasında sızmasın diye sıfırla.
    groq_pool._remaining_tokens.clear()


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
        analyzer.analyze_text = MagicMock(return_value=mock_result)

    result = pooled.analyze_text("test content")

    pooled._analyzers["qwen/qwen3.8-27b"].analyze_text.assert_called_once_with("test content")
    pooled._analyzers["openai/gpt-oss-20b"].analyze_text.assert_not_called()
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
