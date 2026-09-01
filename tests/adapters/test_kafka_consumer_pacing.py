"""kafka_consumer._process kaynaklar-arası/reanalyze-öncesi-sonrası Groq TPM
throttle testleri.

1 Eyl 2026'da canlıda bulundu: update_news_from_source ile reanalyze_missed
arasında VE bir kaynağın işi bitip sıradakine geçilirken hiç bekleme yoktu —
17 kaynak art arda boşluksuz ateşleniyordu, Groq'un TPM kovasını (leaky
bucket) anlık boşaltan 3 burst kaynağından ikisi (bkz. CLAUDE.md roadmap #25,
[[news_service.py::reanalyze_missed]] üçüncüsünü kapatıyor).

DB/Kafka bağımlılıkları (SessionLocal, NewsRepository, ...) bilinçli olarak
mock'landı — bu dosyanın geri kalanı (consume() döngüsü) projede hiç unit
test edilmemiş ağır DI/IO glue kodu; burada SADECE 1 Eyl 2026'da eklenen yeni
throttle davranışı test ediliyor.
"""
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.adapters.messaging import kafka_consumer
from src.infrastructure.config.settings import settings


def _patched_process(mock_service, sleep_mock):
    """kafka_consumer._process'in DB/Kafka bağımlılıklarını mock'layan ortak context manager listesi."""
    return [
        patch("src.adapters.messaging.kafka_consumer.SessionLocal"),
        patch("src.adapters.messaging.kafka_consumer.NewsRepository"),
        patch("src.adapters.messaging.kafka_consumer.SubscriberRepository"),
        patch("src.adapters.messaging.kafka_consumer.PushSubscriptionRepository"),
        patch("src.adapters.messaging.kafka_consumer.build_analyzer"),
        patch("src.adapters.messaging.kafka_consumer.build_web_push"),
        patch("src.adapters.messaging.kafka_consumer._get_search_repo"),
        patch("src.adapters.messaging.kafka_consumer._get_email_adapter"),
        patch("src.adapters.messaging.kafka_consumer.NewsService", return_value=mock_service),
        patch("src.adapters.messaging.kafka_consumer.asyncio.sleep", new=sleep_mock),
    ]


def test_process_paces_before_and_after_reanalyze_missed():
    """update_news_from_source ile reanalyze_missed arasında VE reanalyze_missed
    sonrasında (kaynaklar-arası boşluk için) Groq TPM güvenli bir bekleme olmalı."""
    fake_scraper = MagicMock()
    mock_service = MagicMock()
    mock_service.update_news_from_source = AsyncMock()
    mock_service.reanalyze_missed = MagicMock(return_value=0)
    sleep_mock = AsyncMock()

    patchers = _patched_process(mock_service, sleep_mock)
    for p in patchers:
        p.start()
    try:
        asyncio.run(kafka_consumer._process(fake_scraper))
    finally:
        for p in patchers:
            p.stop()

    mock_service.update_news_from_source.assert_called_once()
    mock_service.reanalyze_missed.assert_called_once_with(3)
    assert sleep_mock.call_count == 2
    for call in sleep_mock.call_args_list:
        assert call.args[0] == settings.groq_request_interval_seconds
