import requests
from bs4 import BeautifulSoup
from typing import List
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article


class BaseRssScraper(NewsScraperPort):
    """Tüm RSS scraper'lar için ortak temel sınıf."""
    url: str = ""
    source_name: str = ""
    limit: int = 25

    def fetch_news(self) -> List[Article]:
        print(f"📡 {self.source_name} kaynağına bağlanılıyor...")
        articles = []
        try:
            r = requests.get(
                self.url, timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "xml")
            items = soup.find_all("item")
            print(f"✅ {len(items)} haber bulundu. İlk {min(self.limit, len(items))} alınıyor.")

            for item in items[:self.limit]:
                title   = item.find("title").text.strip()       if item.find("title")       else "Başlıksız"
                content = item.find("description").text.strip() if item.find("description") else ""
                url     = item.find("link").text.strip()        if item.find("link")        else ""

                articles.append(Article(
                    title=title,
                    content=content,
                    source=self.source_name,
                    url=url,
                ))
        except Exception as e:
            print(f"❌ {self.source_name} hata: {e}")
        return articles


# ── İngilizce Kaynaklar ───────────────────────────────────────────────────────

class BBCTechnologyScraper(BaseRssScraper):
    def __init__(self):
        self.url = "http://feeds.bbci.co.uk/news/technology/rss.xml"
        self.source_name = "BBC Technology"
        self.limit = 25


class BBCSportScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://feeds.bbci.co.uk/sport/rss.xml"
        self.source_name = "BBC Sport"
        self.limit = 25


# ── Türkçe Kaynaklar ──────────────────────────────────────────────────────────

class TRTHaberScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.trthaber.com/sondakika.rss"
        self.source_name = "TRT Haber"
        self.limit = 25


class BBCTurkishScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.bbc.co.uk/turkce/index.xml"
        self.source_name = "BBC Türkçe"
        self.limit = 25


class HurriyetScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.hurriyet.com.tr/rss/anasayfa"
        self.source_name = "Hürriyet"
        self.limit = 25


class HurriyetSporScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.hurriyet.com.tr/rss/spor"
        self.source_name = "Hürriyet Spor"
        self.limit = 25