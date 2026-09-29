"""Kaynak portföyü sözleşmesi (S2, 29 Eylül 2026): kapasite modeli ve konu dengesi kilitli.

Yeni kaynak eklerken bu test kırılırsa başka bir kaynağın tavanı DÜŞÜRÜLÜR — testin tavanı
gevşetilmez (Groq günlük token kotası ve t3.small bu bütçeye göre boyutlandırıldı)."""

from src.adapters.scrapers.registry import SCRAPER_REGISTRY
from src.domain.scoring.credibility import SOURCE_CREDIBILITY
from src.domain.topics import VALID_TOPIC_IDS
from src.infrastructure.config.settings import settings

DAILY_BUDGET = 950   # spec §5: çeviri sonrası kapasite ≈ 900-950 analiz/gün
UNFOCUSED_TOPICS = {"Politics", "Other"}   # genel kaynaklar zaten bunları doldurur


def test_every_source_declares_a_valid_profile():
    for name, scraper in SCRAPER_REGISTRY.items():
        assert scraper.language in {"TR", "EN"}, name
        assert scraper.focus_topic is None or scraper.focus_topic in VALID_TOPIC_IDS, name
        assert isinstance(scraper.daily_cap, int) and scraper.daily_cap > 0, name


def test_sum_of_daily_caps_fits_the_capacity_budget():
    assert sum(s.daily_cap for s in SCRAPER_REGISTRY.values()) <= DAILY_BUDGET


def test_every_focused_topic_has_at_least_one_dedicated_source():
    covered = {s.focus_topic for s in SCRAPER_REGISTRY.values() if s.focus_topic}
    assert (VALID_TOPIC_IDS - UNFOCUSED_TOPICS) <= covered, sorted((VALID_TOPIC_IDS - UNFOCUSED_TOPICS) - covered)


def test_no_single_topic_dominates_the_dedicated_budget():
    """Denge: hiçbir konunun odaklı kaynak tavanları, toplam odaklı bütçenin %35'ini aşmaz."""
    per_topic = {}
    for s in SCRAPER_REGISTRY.values():
        if s.focus_topic:
            per_topic[s.focus_topic] = per_topic.get(s.focus_topic, 0) + s.daily_cap
    total = sum(per_topic.values())
    for topic, cap in per_topic.items():
        assert cap <= 0.35 * total, f"{topic}: {cap}/{total}"


def test_every_source_has_credibility_and_is_scheduled():
    scheduled = {n.strip() for n in settings.scrape_sources.split(",")}
    for name in SCRAPER_REGISTRY:
        assert name in SOURCE_CREDIBILITY, f"{name}: credibility.py satırı yok"
        assert name in scheduled, f"{name}: settings.scrape_sources'ta yok"
    assert scheduled == set(SCRAPER_REGISTRY), scheduled ^ set(SCRAPER_REGISTRY)
