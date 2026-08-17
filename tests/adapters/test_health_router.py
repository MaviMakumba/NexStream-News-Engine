import pytest
from unittest.mock import patch, MagicMock


def _fake_request():
    """slowapi rate limit decorator'ı (v1.17 güvenlik denetimi) gerçek bir
    starlette Request bekliyor — handler'lar TestClient yerine doğrudan
    çağrıldığı için (TestClient Kafka loop'u kırıyor) minimal bir scope ile
    sahte Request üretilir."""
    from starlette.requests import Request
    return Request({
        "type": "http", "method": "GET", "path": "/health",
        "headers": [], "query_string": b"", "client": ("127.0.0.1", 1234),
    })


# ── /health endpoint — handler direkt çağrılıyor (TestClient Kafka loop'u kırar) ──

def _call_health(db="ok", kafka="ok", chromadb=("ok", 42), embedder="ok", email="console (mail gönderilmiyor)"):
    """Tüm bağımlılık kontrollerini mock'layarak health_check'i çağırır.

    HEPSİ mock'lanmalı — biri açıkta kalırsa test gerçek bir bağlantı
    (Postgres/soket/HTTP) denemesi yapıp saniyelerce bekler ve ortama göre
    farklı sonuç verir.
    """
    from src.adapters.api.routers.health_router import health_check
    base = "src.adapters.api.routers.health_router."
    with patch(base + "_check_db", return_value=db), \
         patch(base + "_check_kafka", return_value=kafka), \
         patch(base + "_check_chromadb", return_value=chromadb), \
         patch(base + "_check_embedder", return_value=embedder), \
         patch(base + "_check_email", return_value=email):
        return health_check(_fake_request())


def test_health_returns_ok_when_all_services_up():
    result = _call_health(chromadb=("ok", 42))
    assert result["status"] == "ok"
    assert result["db"] == "ok"
    assert result["kafka"] == "ok"
    assert result["chromadb"] == "ok"
    assert result["indexed_articles"] == 42


def test_health_returns_degraded_when_db_down():
    result = _call_health(db="error", chromadb=("ok", 0))
    assert result["status"] == "degraded"
    assert result["db"] == "error"


def test_health_returns_degraded_when_kafka_down():
    result = _call_health(kafka="error", chromadb=("ok", 0))
    assert result["status"] == "degraded"
    assert result["kafka"] == "error"


def test_health_returns_degraded_when_chromadb_down():
    result = _call_health(chromadb=("error", 0))
    assert result["status"] == "degraded"
    assert result["chromadb"] == "error"
    assert result["indexed_articles"] == 0


def test_health_response_has_all_required_fields():
    result = _call_health(chromadb=("ok", 100))
    assert set(result.keys()) == {
        "status", "db", "kafka", "chromadb", "embedder", "email", "indexed_articles"
    }


# ── embedder servisi ──────────────────────────────────────────────────────────

def test_health_embedder_ok_raporlar():
    assert _call_health(embedder="ok")["embedder"] == "ok"


def test_health_embedder_down_ise_status_degraded():
    result = _call_health(embedder="down")
    assert result["embedder"] == "down"
    assert result["status"] != "ok"


def test_check_embedder_ok_on_200():
    from src.adapters.api.routers.health_router import _check_embedder
    with patch("httpx.get", return_value=MagicMock(status_code=200)):
        assert _check_embedder() == "ok"


def test_check_embedder_down_on_non_200():
    from src.adapters.api.routers.health_router import _check_embedder
    with patch("httpx.get", return_value=MagicMock(status_code=503)):
        assert _check_embedder() == "down"


def test_check_embedder_down_on_exception():
    """Servis hiç ayakta değilse /health 500 vermemeli, sadece down demeli."""
    from src.adapters.api.routers.health_router import _check_embedder
    with patch("httpx.get", side_effect=Exception("baglanti yok")):
        assert _check_embedder() == "down"


# ── E-posta adapter'ı ────────────────────────────────────────────────────────

def test_check_email_reports_smtp():
    """Kimlik bilgileri dolu bir SmtpEmailAdapter — sade "smtp" raporlanmalı."""
    from src.adapters.api.routers.health_router import _check_email
    from src.adapters.notifications.email_adapter import SmtpEmailAdapter
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()
    with patch("src.adapters.api.routers.health_router.get_email_adapter", return_value=adapter):
        assert _check_email() == "smtp"


def test_check_email_reports_smtp_missing_credentials():
    """EMAIL_PROVIDER=smtp seçilip SMTP_USER/SMTP_PASSWORD boş bırakılırsa
    (get_email_adapter yine de bir SmtpEmailAdapter döner — bilinçli) /health
    bunu sade "smtp" yerine ayırt edilebilir bir uyarıyla raporlamalı (Finding 3):
    aksi halde her gönderim sessizce _deliver()'ın except'inde başarısız olurdu."""
    from src.adapters.api.routers.health_router import _check_email
    from src.adapters.notifications.email_adapter import SmtpEmailAdapter
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()
    with patch("src.adapters.api.routers.health_router.get_email_adapter", return_value=adapter):
        assert _check_email() == "smtp (kimlik eksik)"


def test_check_email_reports_resend():
    from src.adapters.api.routers.health_router import _check_email
    from src.adapters.notifications.email_adapter import ResendEmailAdapter
    with patch("src.adapters.api.routers.health_router.get_email_adapter", return_value=ResendEmailAdapter()):
        assert _check_email() == "resend"


def test_check_email_reports_console_with_warning_suffix():
    from src.adapters.api.routers.health_router import _check_email
    from src.adapters.notifications.email_adapter import ConsoleEmailAdapter
    with patch("src.adapters.api.routers.health_router.get_email_adapter", return_value=ConsoleEmailAdapter()):
        assert _check_email() == "console (mail gönderilmiyor)"


def test_health_includes_email_field_without_affecting_status():
    """email alanı bilgilendirici — dev'de console olması status'u degrade etmemeli."""
    result = _call_health(chromadb=("ok", 1))
    assert "email" in result


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
