import requests
from bs4 import BeautifulSoup
from typing import List
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article


class BaseRssScraper(NewsScraperPort):
    """RSS 2.0 ve Atom feed'leri destekleyen temel sınıf."""
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

            # RSS 2.0 → <item>, Atom → <entry>
            items = soup.find_all("item") or soup.find_all("entry")
            print(f"✅ {len(items)} haber bulundu. İlk {min(self.limit, len(items))} alınıyor.")

            for item in items[:self.limit]:
                title   = item.find("title")
                title   = title.text.strip() if title else "Başlıksız"

                # RSS: <description>, Atom: <summary> veya <content>
                body = (
                    item.find("description")
                    or item.find("summary")
                    or item.find("content")
                )
                content = body.text.strip() if body else ""

                # RSS: <link> text, Atom: <link href="...">
                link_tag = item.find("link")
                if link_tag:
                    url = link_tag.get("href") or link_tag.text.strip()
                else:
                    url = ""

                articles.append(Article(
                    title=title,
                    content=content,
                    source=self.source_name,
                    url=url,
                ))
        except Exception as e:
            print(f"❌ {self.source_name} hata: {e}")
        return articles


# ── Türkçe Kaynaklar ──────────────────────────────────────────────────────────

class TRTHaberScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.trthaber.com/sondakika.rss"
        self.source_name = "TRT Haber"
        self.limit = 25


class BBCTurkishScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://feeds.bbci.co.uk/turkce/rss.xml"
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


class SabahScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.sabah.com.tr/rss/anasayfa.xml"
        self.source_name = "Sabah"
        self.limit = 25


class CNNTurkScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.cnnturk.com/feed/rss/guncel/rss.xml"
        self.source_name = "CNN Türk"
        self.limit = 25


class SozcuScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.sozcu.com.tr/rss/"
        self.source_name = "Sözcü"
        self.limit = 25


class HaberturkScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.haberturk.com/rss/gundem.xml"
        self.source_name = "Habertürk"
        self.limit = 25


class HaberturkSporScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.haberturk.com/rss/spor.xml"
        self.source_name = "HT Spor"
        self.limit = 25


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
