import pytest
from unittest.mock import patch, MagicMock


# ── /health endpoint — handler direkt çağrılıyor (TestClient Kafka loop'u kırar) ──

def test_health_returns_ok_when_all_services_up():
    from src.adapters.api.routers.health_router import health_check
    with patch("src.adapters.api.routers.health_router._check_db", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_kafka", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_chromadb", return_value=("ok", 42)):
        result = health_check()
    assert result["status"] == "ok"
    assert result["db"] == "ok"
    assert result["kafka"] == "ok"
    assert result["chromadb"] == "ok"
    assert result["indexed_articles"] == 42


def test_health_returns_degraded_when_db_down():
    from src.adapters.api.routers.health_router import health_check
    with patch("src.adapters.api.routers.health_router._check_db", return_value="error"), \
         patch("src.adapters.api.routers.health_router._check_kafka", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_chromadb", return_value=("ok", 0)):
        result = health_check()
    assert result["status"] == "degraded"
    assert result["db"] == "error"


def test_health_returns_degraded_when_kafka_down():
    from src.adapters.api.routers.health_router import health_check
    with patch("src.adapters.api.routers.health_router._check_db", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_kafka", return_value="error"), \
         patch("src.adapters.api.routers.health_router._check_chromadb", return_value=("ok", 0)):
        result = health_check()
    assert result["status"] == "degraded"
    assert result["kafka"] == "error"


def test_health_returns_degraded_when_chromadb_down():
    from src.adapters.api.routers.health_router import health_check
    with patch("src.adapters.api.routers.health_router._check_db", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_kafka", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_chromadb", return_value=("error", 0)):
        result = health_check()
    assert result["status"] == "degraded"
    assert result["chromadb"] == "error"
    assert result["indexed_articles"] == 0


def test_health_response_has_all_required_fields():
    from src.adapters.api.routers.health_router import health_check
    with patch("src.adapters.api.routers.health_router._check_db", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_kafka", return_value="ok"), \
         patch("src.adapters.api.routers.health_router._check_chromadb", return_value=("ok", 100)):
        result = health_check()
    assert set(result.keys()) == {"status", "db", "kafka", "chromadb", "indexed_articles"}


# ── Dahili kontrol fonksiyonları ──────────────────────────────────────────────

def test_check_db_returns_ok_on_success():
    from src.adapters.api.routers.health_router import _check_db
    mock_db = MagicMock()
    with patch("src.adapters.api.routers.health_router.SessionLocal", return_value=mock_db):
        assert _check_db() == "ok"


def test_check_db_returns_error_on_exception():
    from src.adapters.api.routers.health_router import _check_db
    with patch("src.adapters.api.routers.health_router.SessionLocal", side_effect=Exception("conn fail")):
        assert _check_db() == "error"


def test_check_kafka_returns_ok_on_success():
    from src.adapters.api.routers.health_router import _check_kafka
    with patch("socket.create_connection", return_value=MagicMock()):
        assert _check_kafka() == "ok"


def test_check_kafka_returns_error_on_timeout():
    from src.adapters.api.routers.health_router import _check_kafka
    with patch("socket.create_connection", side_effect=OSError("timeout")):
        assert _check_kafka() == "error"


def test_check_chromadb_returns_ok_and_count():
    import src.adapters.api.routers.health_router as hr
    from src.adapters.api.routers.health_router import _check_chromadb
    hr._chroma_client = None  # reset singleton so the mock is actually called
    mock_collection = MagicMock()
    mock_collection.count.return_value = 99
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    with patch("src.adapters.api.routers.health_router.chromadb.HttpClient", return_value=mock_client):
        status, count = _check_chromadb()
    assert status == "ok"
    assert count == 99


def test_check_chromadb_returns_error_on_exception():
    import src.adapters.api.routers.health_router as hr
    from src.adapters.api.routers.health_router import _check_chromadb
    hr._chroma_client = None  # reset singleton so the mock is actually called
    with patch("src.adapters.api.routers.health_router.chromadb.HttpClient", side_effect=Exception("unreachable")):
        status, count = _check_chromadb()
    assert status == "error"
    assert count == 0
