from types import SimpleNamespace
from unittest.mock import patch

from src.adapters.messaging.kafka_consumer import _daily_cap_for


def _scraper(name="CNN Türk", cap=120):
    return SimpleNamespace(source_name=name, daily_cap=cap)


def test_daily_cap_defaults_to_the_scrapers_own_cap():
    with patch("src.adapters.messaging.kafka_consumer.settings") as s:
        s.source_daily_caps = ""
        assert _daily_cap_for(_scraper()) == 120


def test_env_override_wins_over_scraper_default():
    with patch("src.adapters.messaging.kafka_consumer.settings") as s:
        s.source_daily_caps = '{"CNN Türk": 80}'
        assert _daily_cap_for(_scraper()) == 80


def test_scraper_without_cap_attribute_is_unlimited():
    with patch("src.adapters.messaging.kafka_consumer.settings") as s:
        s.source_daily_caps = ""
        assert _daily_cap_for(SimpleNamespace(source_name="X")) is None
