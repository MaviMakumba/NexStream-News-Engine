import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    with patch("src.infrastructure.config.database.engine") as mock_engine, \
         patch("src.infrastructure.config.database.Base") as mock_base, \
         patch("src.adapters.messaging.kafka_publisher.KafkaPublisherAdapter") as mock_kafka, \
         patch("src.dependencies.get_search_repository"):
        mock_engine.connect = MagicMock()
        mock_base.metadata.create_all = MagicMock()
        mock_kafka_instance = MagicMock()
        mock_kafka_instance.start = MagicMock()
        mock_kafka_instance.stop = MagicMock()
        mock_kafka.return_value = mock_kafka_instance

        import importlib
        import src.main
        importlib.reload(src.main)
        from src.main import app
        from fastapi.testclient import TestClient
        yield TestClient(app)


def test_metrics_endpoint_returns_200(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_contains_http_request_metrics(client):
    client.get("/")
    response = client.get("/metrics")
    body = response.text
    assert "http_request" in body


def test_metrics_contains_custom_nexstream_metrics(client):
    response = client.get("/metrics")
    body = response.text
    assert "nexstream_articles_processed" in body or "nexstream_groq_latency" in body or "nexstream_search_latency" in body


def test_custom_counter_increments():
    from src.adapters.api.metrics import articles_processed_total
    before = articles_processed_total.labels(source="TestSource", status="saved")._value.get()
    articles_processed_total.labels(source="TestSource", status="saved").inc()
    after = articles_processed_total.labels(source="TestSource", status="saved")._value.get()
    assert after == before + 1


def test_custom_histogram_observes():
    from src.adapters.api.metrics import groq_latency_seconds
    groq_latency_seconds.observe(1.5)
    assert groq_latency_seconds._sum.get() > 0


def test_search_latency_histogram():
    from src.adapters.api.metrics import search_latency_seconds
    search_latency_seconds.observe(0.05)
    assert search_latency_seconds._sum.get() > 0


def test_groq_rate_limit_counter():
    from src.adapters.api.metrics import groq_rate_limit_total
    before = groq_rate_limit_total._value.get()
    groq_rate_limit_total.inc()
    after = groq_rate_limit_total._value.get()
    assert after == before + 1


def test_groq_tokens_total_counter():
    """roadmap #25 — Groq'un gerçek usage alanından beslenen token sayacı."""
    from src.adapters.api.metrics import groq_tokens_total
    before = groq_tokens_total.labels(model="openai/gpt-oss-20b", kind="prompt")._value.get()
    groq_tokens_total.labels(model="openai/gpt-oss-20b", kind="prompt").inc(530)
    after = groq_tokens_total.labels(model="openai/gpt-oss-20b", kind="prompt")._value.get()
    assert after == before + 530
