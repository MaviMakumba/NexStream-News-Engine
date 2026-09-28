"""Worker'ın Kafka kuyruğunda bayat scrape emirlerini atlaması + uzun işleme
süresine rağmen consumer group'ta kalması.

28 Eyl 2026'da prod taramasında bulundu: scheduler 10 dk'da bir 17 emir
üretirken worker Groq rate-limit beklemeleri yüzünden bir kaynağı ~12 dk'da
bitiriyordu — `news_updates`'ta 38.881 mesajlık, hiç erimeyen bir backlog
birikmişti. Ayrıca aiokafka'nın varsayılan max_poll_interval_ms'i (5 dk) tek
bir mesajın işlenme süresinden kısa olduğu için worker sürekli gruptan
atılıyordu (rpk: STATE Empty, MEMBERS 0).

Bir scrape emri "bu kaynağı ŞİMDİ tara" demek — eskimiş bir emri işlemek
hiçbir şey kazandırmaz, aynı kaynak zaten sonraki scheduler turunda yeniden
istenecek.
"""
from unittest.mock import patch

from src.adapters.messaging import kafka_consumer
from src.infrastructure.config.settings import settings


NOW = 1_800_000_000.0  # sabit "şimdi" (epoch saniye)


def test_fresh_command_is_not_stale():
    ts_ms = int((NOW - 60) * 1000)
    assert kafka_consumer._is_stale_command(ts_ms, now=NOW) is False


def test_command_older_than_threshold_is_stale():
    ts_ms = int((NOW - settings.worker_stale_command_seconds - 1) * 1000)
    assert kafka_consumer._is_stale_command(ts_ms, now=NOW) is True


def test_missing_timestamp_is_never_stale():
    """Timestamp'i olmayan (None/-1) bir mesajı atlamak veri kaybı olurdu — işle."""
    assert kafka_consumer._is_stale_command(None, now=NOW) is False
    assert kafka_consumer._is_stale_command(-1, now=NOW) is False


def test_stale_check_disabled_when_threshold_zero(monkeypatch):
    monkeypatch.setattr(settings, "worker_stale_command_seconds", 0)
    ts_ms = int((NOW - 10 * 24 * 3600) * 1000)
    assert kafka_consumer._is_stale_command(ts_ms, now=NOW) is False


def test_consumer_poll_interval_exceeds_long_processing_time():
    """Tek bir kaynak Groq beklemeleriyle 10+ dk sürebiliyor — varsayılan 5 dk'lık
    max_poll_interval worker'ı gruptan attırıyordu."""
    with patch("src.adapters.messaging.kafka_consumer.AIOKafkaConsumer") as cls:
        kafka_consumer._build_consumer()
    kwargs = cls.call_args.kwargs
    assert kwargs["group_id"] == "news_workers_group"
    assert kwargs["max_poll_interval_ms"] >= 30 * 60 * 1000
