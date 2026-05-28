import logging
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article

logger = logging.getLogger(__name__)


def _parse_pub_date(item) -> Optional[datetime]:
    tag = item.find("pubDate") or item.find("published") or item.find("updated")
    if not tag:
        return None
    text = tag.text.strip()
    try:
        return parsedate_to_datetime(text)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


class BaseRssScraper(NewsScraperPort):
    url: str = ""
    source_name: str = ""
    limit: int = 25

    async def _fetch_content(self, url: str) -> bytes:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.content

    async def fetch_news(self) -> List[Article]:
        logger.info("%s kaynağına bağlanılıyor...", self.source_name)
        articles = []
        try:
            content = await self._fetch_content(self.url)
            soup = BeautifulSoup(content, "xml")

            items = soup.find_all("item") or soup.find_all("entry")
            logger.info("%s: %d haber bulundu, ilk %d alınıyor.", self.source_name, len(items), min(self.limit, len(items)))

            for item in items[:self.limit]:
                title = item.find("title")
                title = title.text.strip() if title else "Başlıksız"

                body = (
                    item.find("description")
                    or item.find("summary")
                    or item.find("content")
                )
                content_text = body.text.strip() if body else ""

                link_tag = item.find("link")
                if link_tag:
                    url = link_tag.get("href") or link_tag.text.strip()
                else:
                    url = ""

                articles.append(Article(
                    title=title,
                    content=content_text,
                    source=self.source_name,
                    url=url,
                    published_at=_parse_pub_date(item),
                ))
        except Exception as e:
            logger.error("%s hata: %s", self.source_name, e)
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


class GuardianTechScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.theguardian.com/technology/rss"
        self.source_name = "Guardian Tech"
        self.limit = 25


class TechCrunchScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://techcrunch.com/feed/"
        self.source_name = "TechCrunch"
        self.limit = 25


class HackerNewsScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://hnrss.org/frontpage"
        self.source_name = "Hacker News"
        self.limit = 25


class TheVergeScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.theverge.com/rss/index.xml"
        self.source_name = "The Verge"
        self.limit = 25


# ── Yeni Türkçe Kaynaklar (v1.8) ──────────────────────────────────────────────

class AnadoluAjansiScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.aa.com.tr/tr/rss/default?cat=guncel"
        self.source_name = "Anadolu Ajansı"
        self.limit = 25


class AnadoluEkonomiScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"
        self.source_name = "AA Ekonomi"
        self.limit = 25
