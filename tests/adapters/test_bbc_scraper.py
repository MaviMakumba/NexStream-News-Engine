from unittest.mock import patch, MagicMock
from src.adapters.scrapers.bbc_scraper import BBCRssScraper
from src.domain.models.article import Article

# Sahte RSS XML — gerçek BBC formatında
FAKE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Test Haberi 1</title>
      <description>Test içeriği 1</description>
      <link>https://bbc.com/test1</link>
    </item>
    <item>
      <title>Test Haberi 2</title>
      <description>Test içeriği 2</description>
      <link>https://bbc.com/test2</link>
    </item>
  </channel>
</rss>""".encode("utf-8")

def make_mock_response(content=FAKE_RSS, status_code=200):
    mock = MagicMock()
    mock.content = content
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock

@patch("src.adapters.scrapers.bbc_scraper.requests.get")
def test_fetch_returns_articles(mock_get):
    """Scraper Article listesi döndürüyor mu?"""
    mock_get.return_value = make_mock_response()
    scraper = BBCRssScraper()
    articles = scraper.fetch_news()

    assert len(articles) == 2
    assert all(isinstance(a, Article) for a in articles)

@patch("src.adapters.scrapers.bbc_scraper.requests.get")
def test_fetch_maps_fields_correctly(mock_get):
    """Alanlar doğru eşleniyor mu?"""
    mock_get.return_value = make_mock_response()
    scraper = BBCRssScraper()
    article = scraper.fetch_news()[0]

    assert article.title == "Test Haberi 1"
    assert article.content == "Test içeriği 1"
    assert article.url == "https://bbc.com/test1"
    assert article.source == "BBC Technology"

@patch("src.adapters.scrapers.bbc_scraper.requests.get")
def test_fetch_max_five_articles(mock_get):
    """En fazla 5 haber alınıyor mu?"""
    many_items = "".join([
        f"<item><title>H{i}</title><description>C{i}</description>"
        f"<link>https://bbc.com/{i}</link></item>"
        for i in range(10)
    ])
    rss = f"""<?xml version="1.0"?><rss><channel>{many_items}</channel></rss>"""
    mock_get.return_value = make_mock_response(rss.encode())

    articles = BBCRssScraper().fetch_news()
    assert len(articles) == 5

@patch("src.adapters.scrapers.bbc_scraper.requests.get")
def test_fetch_returns_empty_on_error(mock_get):
    """Hata durumunda boş liste dönmeli"""
    mock_get.side_effect = Exception("Bağlantı hatası")
    articles = BBCRssScraper().fetch_news()
    assert articles == []