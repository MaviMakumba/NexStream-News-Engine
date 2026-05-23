import asyncio
from unittest.mock import AsyncMock, patch
from src.adapters.scrapers.rss_scrapers import BBCTechnologyScraper, CNNTurkScraper, _parse_pub_date
from bs4 import BeautifulSoup


RSS_WITH_PUBDATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Article</title>
    <description>Content</description>
    <link>https://example.com/1</link>
    <pubDate>Wed, 21 May 2025 14:30:00 +0000</pubDate>
  </item>
</channel></rss>"""

ATOM_WITH_PUBLISHED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Atom Article</title>
    <summary>Content</summary>
    <link href="https://example.com/atom-1"/>
    <published>2025-05-21T14:30:00Z</published>
  </entry>
</feed>"""

RSS_WITHOUT_DATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>No Date Article</title>
    <description>Content</description>
    <link>https://example.com/2</link>
  </item>
</channel></rss>"""


def test_rss_pubdate_parsed_correctly():
    scraper = BBCTechnologyScraper()
    with patch.object(scraper, "_fetch_content", new=AsyncMock(return_value=RSS_WITH_PUBDATE.encode())):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].published_at is not None
    assert articles[0].published_at.year == 2025
    assert articles[0].published_at.month == 5
    assert articles[0].published_at.day == 21


def test_atom_published_parsed_correctly():
    scraper = CNNTurkScraper()
    with patch.object(scraper, "_fetch_content", new=AsyncMock(return_value=ATOM_WITH_PUBLISHED.encode())):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].published_at is not None
    assert articles[0].published_at.year == 2025


def test_missing_pubdate_returns_none():
    scraper = BBCTechnologyScraper()
    with patch.object(scraper, "_fetch_content", new=AsyncMock(return_value=RSS_WITHOUT_DATE.encode())):
        articles = asyncio.run(scraper.fetch_news())
    assert articles[0].published_at is None


def test_parse_pub_date_rss_format():
    soup = BeautifulSoup("<item><pubDate>Mon, 19 May 2025 10:00:00 GMT</pubDate></item>", "xml")
    item = soup.find("item")
    dt = _parse_pub_date(item)
    assert dt is not None
    assert dt.year == 2025


def test_parse_pub_date_iso_format():
    soup = BeautifulSoup("<entry><published>2025-05-19T10:00:00Z</published></entry>", "xml")
    item = soup.find("entry")
    dt = _parse_pub_date(item)
    assert dt is not None
    assert dt.year == 2025


def test_parse_pub_date_no_tag_returns_none():
    soup = BeautifulSoup("<item><title>No date</title></item>", "xml")
    item = soup.find("item")
    assert _parse_pub_date(item) is None
