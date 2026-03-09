import pytest
from unittest.mock import patch, MagicMock
from src.adapters.scrapers.rss_scrapers import (
    BBCTechnologyScraper,
    BBCSportScraper,
    TRTHaberScraper,
    BBCTurkishScraper,
    HurriyetScraper,
    HurriyetSporScraper,
    BaseRssScraper,
)
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
    </item>
    <item>
      <title>Test Article Two</title>
      <description>Second test article content.</description>
      <link>https://example.com/article-2</link>
    </item>
  </channel>
</rss>"""

def make_mock_response(content=SAMPLE_RSS, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.content = content.encode("utf-8")
    mock.raise_for_status = MagicMock()
    return mock

# ── BaseRssScraper ────────────────────────────────────────────────────────────

def test_base_scraper_returns_articles():
    """BaseRssScraper RSS'i parse edip Article listesi döndürür."""
    scraper = BBCTechnologyScraper()
    with patch("requests.get", return_value=make_mock_response()):
        articles = scraper.fetch_news()
    assert len(articles) == 2
    assert all(isinstance(a, Article) for a in articles)

def test_base_scraper_maps_fields_correctly():
    """Başlık, içerik ve URL doğru Article alanlarına atanır."""
    scraper = BBCTechnologyScraper()
    with patch("requests.get", return_value=make_mock_response()):
        articles = scraper.fetch_news()
    assert articles[0].title == "Test Article One"
    assert articles[0].content == "First test article content."
    assert articles[0].url == "https://example.com/article-1"

def test_base_scraper_sets_source_name():
    """Her scraper kendi source_name'ini Article'a atar."""
    scraper = TRTHaberScraper()
    with patch("requests.get", return_value=make_mock_response()):
        articles = scraper.fetch_news()
    assert articles[0].source == "TRT Haber"

def test_base_scraper_returns_empty_on_error():
    """Bağlantı hatasında boş liste döner, exception fırlatmaz."""
    scraper = BBCTechnologyScraper()
    with patch("requests.get", side_effect=Exception("Connection error")):
        articles = scraper.fetch_news()
    assert articles == []

def test_base_scraper_respects_limit():
    """Scraper limit kadar haber döndürür."""
    scraper = BBCTechnologyScraper()
    scraper.limit = 1
    with patch("requests.get", return_value=make_mock_response()):
        articles = scraper.fetch_news()
    assert len(articles) == 1

# ── Her Scraper'ın source_name'i doğru ───────────────────────────────────────

@pytest.mark.parametrize("scraper_class,expected_source", [
    (BBCTechnologyScraper, "BBC Technology"),
    (BBCSportScraper,      "BBC Sport"),
    (TRTHaberScraper,      "TRT Haber"),
    (BBCTurkishScraper,    "BBC Türkçe"),
    (HurriyetScraper,      "Hürriyet"),
    (HurriyetSporScraper,  "Hürriyet Spor"),
])
def test_each_scraper_has_correct_source_name(scraper_class, expected_source):
    """Her scraper sınıfının source_name'i doğru tanımlanmış."""
    scraper = scraper_class()
    with patch("requests.get", return_value=make_mock_response()):
        articles = scraper.fetch_news()
    assert articles[0].source == expected_source

# ── Her Scraper'ın URL'i dolu ─────────────────────────────────────────────────

@pytest.mark.parametrize("scraper_class", [
    BBCTechnologyScraper,
    BBCSportScraper,
    TRTHaberScraper,
    BBCTurkishScraper,
    HurriyetScraper,
    HurriyetSporScraper,
])
def test_each_scraper_has_url(scraper_class):
    """Her scraper sınıfının URL'i boş değil."""
    scraper = scraper_class()
    assert scraper.url != ""
    assert scraper.url.startswith("http")