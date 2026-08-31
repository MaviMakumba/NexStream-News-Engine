import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def _no_real_sentry_calls():
    """`sentry_sdk.init()`'in HİÇBİR test sırasında gerçekten çağrılmamasını
    garanti eder — `.env`'de (yerel geliştirmede kazayla) gerçek bir SENTRY_DSN
    dursa bile.

    25 Ağu 2026'da bulundu: `app_client` fixture'ı `src.main`'i reload eder,
    o da modül seviyesinde `init_sentry("app")` çağırır (main.py:48) — bu hiç
    mock'lanmıyordu. Yerel `.env`'e prod aktivasyonu için gerçek DSN eklenince
    HER lokal test koşusu (router testlerinin büyük kısmı `app_client`
    kullanıyor) sessizce gerçek Sentry'ye event gönderdi. `tests/infrastructure/
    test_sentry.py`'deki testler `init_sentry()`'yi kendi başına doğru test
    ediyor (settings + sentry_sdk.init ayrı ayrı mock'lanıyor) — bu fixture
    onların YERİNE geçmiyor, sadece test SÜİTİNİN GENELİNİ gerçek ağ
    çağrısından izole ediyor (autouse — hiçbir testin unutmasına gerek yok)."""
    with patch("sentry_sdk.init"):
        yield


@pytest.fixture(autouse=True)
def _no_real_email_calls():
    """`smtplib.SMTP`/`requests.post`'un HİÇBİR test sırasında gerçek bir ağ
    bağlantısı açmamasını garanti eder — `.env`'de (yerel geliştirmede)
    gerçek SMTP_USER/SMTP_PASSWORD ve RESEND_API_KEY dursa bile.

    27 Ağu 2026'da canlıda bulundu (Sentry'nin 25 Ağu'daki sızıntısıyla
    BİREBİR AYNI bug sınıfı): `test_auth_router.py`'deki birden fazla
    register testi `get_email_adapter`'ı hiç mock'lamıyordu — her tam test
    koşusunda `auth_router.register()`'ın koşulsuz çağırdığı
    `_send_verification_email` GERÇEK SMTP kimlik bilgileriyle gerçek bir
    doğrulama maili gönderdi (test@/new@/ok@example.com — Null MX, kullanıcının
    kendi Gmail'ine bounce olarak geri döndü; Boss@Company.com ise gerçek bir
    üçüncü tarafa gitmiş olabilirdi). Sentry'deki gibi TEK bir yeri mock'lamak
    (`get_email_adapter`) yeterli değil — yeni bir router/endpoint aynı hatayı
    tekrar yapabilir. Bunun yerine ağ SINIRININ kendisi (`smtplib.SMTP` +
    Resend'in kullandığı `requests.post`) kapatılıyor — hangi kod yolu
    çağırırsa çağırsın gerçek bir bağlantı asla açılamaz. Var olan testlerin
    kendi `patch("smtplib.SMTP", ...)`/`patch("requests.post", ...)` blokları
    bunun ÜSTÜNE güvenle katmanlanır (mock.patch iç içe geçince normal şekilde
    geri yüklenir), bu fixture onların yerine geçmiyor, sadece unutulursa
    diye bir güvenlik ağı."""
    with patch("smtplib.SMTP"), patch("requests.post"):
        yield


@pytest.fixture
def app_client():
    """
    DB ve Kafka bağlantısı olmadan FastAPI TestClient döner.
    Tüm HTTP katmanı testleri bu fixture'ı kullanmalı.

    `SessionLocal` de patch'lenmeli, sadece `engine` YETMEZ: `main.py`'deki
    `usage_tracking_middleware` her /api/v1/ isteğinden sonra `_log_api_usage`
    background task'ını açıyor, o da `SessionLocal()` ile GERÇEK bir psycopg2
    bağlantısı deniyordu. psycopg2 senkron olduğu için bu çağrı event loop'u
    bağlantı timeout'u boyunca (~2sn) bloke ediyordu; hata `except`'te
    yutulduğu için testler geçiyor ama her biri 2 saniye yavaşlıyordu
    (29 Tem 2026'da cProfile ile bulundu: 124sn'lik bir koşunun 108sn'i
    psycopg2 `_connect` içindeydi).
    """
    async def _noop_broadcast(*args, **kwargs):
        """Test sırasında DB polling task'ını bastır."""
        await asyncio.sleep(9999)

    with patch("src.infrastructure.config.database.engine") as mock_engine, \
         patch("src.infrastructure.config.database.Base") as mock_base, \
         patch("src.infrastructure.config.database.SessionLocal"), \
         patch("src.adapters.messaging.kafka_publisher.KafkaPublisherAdapter") as mock_kafka, \
         patch("src.dependencies.get_search_repository"), \
         patch("src.main._broadcast_new_articles", side_effect=_noop_broadcast), \
         patch("src.main.run_newsletter_job", side_effect=_noop_broadcast), \
         patch("src.main.run_retention_job", side_effect=_noop_broadcast):
        mock_base.metadata.create_all = MagicMock()

        mock_kafka_instance = AsyncMock()
        mock_kafka_instance.start = AsyncMock(return_value=None)
        mock_kafka_instance.stop = AsyncMock(return_value=None)
        mock_kafka.return_value = mock_kafka_instance

        import importlib
        import src.main
        importlib.reload(src.main)
        from src.main import app
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            yield client
