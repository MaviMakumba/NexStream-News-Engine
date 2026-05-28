import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.adapters.scrapers.rss_scrapers import (
    BBCTechnologyScraper,
    BBCSportScraper,
    TRTHaberScraper,
    BBCTurkishScraper,
    HurriyetScraper,
    HurriyetSporScraper,
    SabahScraper,
    CNNTurkScraper,
    SozcuScraper,
    HaberturkScraper,
    HaberturkSporScraper,
    GuardianTechScraper,
    TechCrunchScraper,
    HackerNewsScraper,
    TheVergeScraper,
    AnadoluAjansiScraper,
    AnadoluEkonomiScraper,
    BaseRssScraper,
)
from src.adapters.scrapers.registry import SCRAPER_REGISTRY
from src.domain.models.article import Article

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Test Article One</title>
      <description>First test article content.</description>
      <link>https://example.com/article-1</link>
      <pubDate>Wed, 21 May 2025 14:30:00 +0000</pubDate>
    </item>
    <item>
      <title>Test Article Two</title>
      <description>Second test article content.</description>
      <link>https://example.com/article-2</link>
    </item>
  </channel>
</rss>"""

SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Atom Feed</title>
  <entry>
    <title>Atom Article One</title>
    <summary>First atom article content.</summary>
    <link href="https://example.com/atom-1"/>
    <published>2025-05-21T14:30:00Z</published>
  </entry>
  <entry>
    <title>Atom Article Two</title>
    <summary>Second atom article content.</summary>
    <link href="https://example.com/atom-2"/>
  </entry>
</feed>"""


def _mock_fetch(content=SAMPLE_RSS):
    return AsyncMock(return_value=content.encode("utf-8"))

# ── BaseRssScraper — RSS 2.0 ──────────────────────────────────────────────────

def test_base_scraper_returns_articles():
    scraper = BBCTechnologyScraper()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch()):
        articles = asyncio.run(scraper.fetch_news())
    assert len(articles) == 2
    assert all(isinstance(a, Article) for a in articles)

def test_base_scraper_maps_fields_correctly():
    scraper = BBCTechnologyScraper()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch()):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].title == "Test Article One"
    assert articles[0].content == "First test article content."
    assert articles[0].url == "https://example.com/article-1"

def test_base_scraper_sets_source_name():
    scraper = TRTHaberScraper()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch()):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].source == "TRT Haber"

def test_base_scraper_returns_empty_on_error():
    scraper = BBCTechnologyScraper()
    with patch.object(scraper, "_fetch_content", new=AsyncMock(side_effect=Exception("Connection error"))):
        articles = asyncio.run(scraper.fetch_news())
    assert articles == []

def test_base_scraper_respects_limit():
    scraper = BBCTechnologyScraper()
    scraper.limit = 1
    with patch.object(scraper, "_fetch_content", new=_mock_fetch()):
        articles = asyncio.run(scraper.fetch_news())
    assert len(articles) == 1

# ── pub_date parsing ──────────────────────────────────────────────────────────

def test_rss_pub_date_parsed():
    scraper = BBCTechnologyScraper()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch()):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].published_at is not None
    assert articles[0].published_at.year == 2025

def test_missing_pub_date_is_none():
    scraper = BBCTechnologyScraper()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch()):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[1].published_at is None

# ── BaseRssScraper — Atom feed ────────────────────────────────────────────────

def test_atom_feed_is_parsed():
    scraper = CNNTurkScraper()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch(SAMPLE_ATOM)):
        articles = asyncio.run(scraper.fetch_news())
    assert len(articles) == 2
    assert articles[0].title == "Atom Article One"
    assert articles[0].content == "First atom article content."
    assert articles[0].url == "https://example.com/atom-1"

def test_atom_pub_date_parsed():
    scraper = CNNTurkScraper()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch(SAMPLE_ATOM)):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].published_at is not None
    assert articles[0].published_at.year == 2025

# ── Her Scraper'ın source_name'i doğru ───────────────────────────────────────

@pytest.mark.parametrize("scraper_class,expected_source", [
    (BBCTechnologyScraper,  "BBC Technology"),
    (BBCSportScraper,       "BBC Sport"),
    (TRTHaberScraper,       "TRT Haber"),
    (BBCTurkishScraper,     "BBC Türkçe"),
    (HurriyetScraper,       "Hürriyet"),
    (HurriyetSporScraper,   "Hürriyet Spor"),
    (SabahScraper,          "Sabah"),
    (CNNTurkScraper,        "CNN Türk"),
    (SozcuScraper,          "Sözcü"),
    (HaberturkScraper,      "Habertürk"),
    (HaberturkSporScraper,  "HT Spor"),
    (GuardianTechScraper,   "Guardian Tech"),
    (TechCrunchScraper,     "TechCrunch"),
    (HackerNewsScraper,     "Hacker News"),
    (TheVergeScraper,       "The Verge"),
    (AnadoluAjansiScraper,  "Anadolu Ajansı"),
    (AnadoluEkonomiScraper, "AA Ekonomi"),
])
def test_each_scraper_has_correct_source_name(scraper_class, expected_source):
    scraper = scraper_class()
    with patch.object(scraper, "_fetch_content", new=_mock_fetch()):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].source == expected_source

# ── Her Scraper'ın URL'i dolu ─────────────────────────────────────────────────

@pytest.mark.parametrize("scraper_class", [
    BBCTechnologyScraper,
    BBCSportScraper,
    TRTHaberScraper,
    BBCTurkishScraper,
    HurriyetScraper,
    HurriyetSporScraper,
    SabahScraper,
    CNNTurkScraper,
    SozcuScraper,
    HaberturkScraper,
    HaberturkSporScraper,
    GuardianTechScraper,
    TechCrunchScraper,
    HackerNewsScraper,
    TheVergeScraper,
    AnadoluAjansiScraper,
    AnadoluEkonomiScraper,
])
def test_each_scraper_has_url(scraper_class):
    scraper = scraper_class()
    assert scraper.url != ""
    assert scraper.url.startswith("http")

# ── Registry ──────────────────────────────────────────────────────────────────

def test_registry_contains_all_scrapers():
    assert len(SCRAPER_REGISTRY) == 17

def test_registry_values_are_scraper_instances():
    for name, scraper in SCRAPER_REGISTRY.items():
        assert hasattr(scraper, "fetch_news"), f"{name} fetch_news metoduna sahip değil"

def test_registry_keys_match_source_names():
    for key, scraper in SCRAPER_REGISTRY.items():
        assert scraper.source_name == key, f"Registry key '{key}' != source_name '{scraper.source_name}'"
