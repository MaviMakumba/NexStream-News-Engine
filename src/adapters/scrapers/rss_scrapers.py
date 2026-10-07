"""RSS scraper'ları — tüm haber kaynakları BaseRssScraper'dan türetilir.

Yeni kaynak eklemek için: alt sınıf (FEED_URL + SOURCE_NAME) + registry kaydı.
Çekim httpx ile asenkron yapılır; ölü/bozuk besleme worker'ı çökertmez —
exception yutulur, boş liste döner. Kaynak başına 25 haber limiti vardır.
"""

import logging
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article
from src.domain.policies.ingest_policy import sort_newest_first

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
    # Kaynak profili (S2): dil, odak konu (None = genel kaynak; değerler src/domain/topics.py
    # kimlikleri) ve günlük tavan (None = sınırsız). Tavan toplamı test_source_portfolio.py ile
    # kapasite modeline (≤ 950/gün) kilitli; operasyonel geçersiz kılma: SOURCE_DAILY_CAPS.
    language: str = "TR"
    focus_topic: Optional[str] = None
    daily_cap: Optional[int] = None

    # Bare "Mozilla/5.0" klasik bot imzasıdır — gerçek tarayıcılar hiçbir zaman
    # tek başına göndermez. AA'nın WAF'ı bunu tanıyıp bağlantıyı TLS seviyesinde
    # reddediyor (9 Eylül 2026'da AA/AA Ekonomi'nin 9 gündür sessiz kaldığı
    # bulunduğunda doğrulandı). Gerçekçi tam bir Chrome UA'sı kullan.
    _USER_AGENT = BROWSER_USER_AGENT

    async def _fetch_content(self, url: str) -> bytes:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.get(url, timeout=10, headers={"User-Agent": self._USER_AGENT})
            r.raise_for_status()
            return r.content

    async def fetch_news(self) -> List[Article]:
        logger.info("%s kaynağına bağlanılıyor...", self.source_name)
        articles = []
        try:
            content = await self._fetch_content(self.url)
            soup = BeautifulSoup(content, "xml")

            items = soup.find_all("item") or soup.find_all("entry")
            logger.info("%s: %d haber bulundu, en yeni %d alınıyor.", self.source_name, len(items), min(self.limit, len(items)))

            for item in items:
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
            # Önce HEPSİNİ ayrıştır, tarihe göre sırala, SONRA dilimle: tarih sırasız feed'lerde
            # (ScienceDaily 60, BBC Health 52 öğe) "ilk N" taze haberi kaçırıp bayatı alıyordu.
            articles = sort_newest_first(articles)[:self.limit]
        except Exception as e:
            # type(e).__name__: httpx.ReadTimeout gibi istisnaların str()'i boş.
            logger.error("%s hata: %s: %s", self.source_name, type(e).__name__, e)
        return articles


# ── Türkçe Kaynaklar ──────────────────────────────────────────────────────────

class TRTHaberScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.trthaber.com/sondakika.rss"
        self.source_name = "TRT Haber"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 70
        self.limit = 25


class BBCTurkishScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://feeds.bbci.co.uk/turkce/rss.xml"
        self.source_name = "BBC Türkçe"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 20
        self.limit = 25


class HurriyetScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.hurriyet.com.tr/rss/anasayfa"
        self.source_name = "Hürriyet"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 50
        self.limit = 25


class HurriyetSporScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.hurriyet.com.tr/rss/spor"
        self.source_name = "Hürriyet Spor"
        self.language = "TR"
        self.focus_topic = "Sports"
        self.daily_cap = 40
        self.limit = 25


class SabahScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.sabah.com.tr/rss/anasayfa.xml"
        self.source_name = "Sabah"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 40
        self.limit = 25


class CNNTurkScraper(BaseRssScraper):
    def __init__(self):
        # 31 Ağu 2026: eski URL (feed/rss/guncel/rss.xml) CNN Türk'ün KENDİ
        # tarafında donmuş — 1 Temmuz 2026'dan beri hiç güncellenmiyor (200
        # dönüyor ama içerik ~2 ay eski), bu yüzden CNN Türk hiç haber
        # kazandırmıyordu (dedup her seferinde aynı eski URL'leri görüyordu).
        # feed/rss/all/news canlı doğrulandı (güncel pubDate), aynı yapı.
        self.url = "https://www.cnnturk.com/feed/rss/all/news"
        self.source_name = "CNN Türk"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 80
        self.limit = 25


class SozcuScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.sozcu.com.tr/rss/"
        self.source_name = "Sözcü"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 70
        self.limit = 25


class HaberturkScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.haberturk.com/rss/gundem.xml"
        self.source_name = "Habertürk"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 60
        self.limit = 25


class HaberturkSporScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.haberturk.com/rss/spor.xml"
        self.source_name = "HT Spor"
        self.language = "TR"
        self.focus_topic = "Sports"
        self.daily_cap = 45
        self.limit = 25


# ── İngilizce Kaynaklar ───────────────────────────────────────────────────────

class BBCTechnologyScraper(BaseRssScraper):
    def __init__(self):
        self.url = "http://feeds.bbci.co.uk/news/technology/rss.xml"
        self.source_name = "BBC Technology"
        self.language = "EN"
        self.focus_topic = "Technology"
        self.daily_cap = 10
        self.limit = 25


class BBCSportScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://feeds.bbci.co.uk/sport/rss.xml"
        self.source_name = "BBC Sport"
        self.language = "EN"
        self.focus_topic = "Sports"
        self.daily_cap = 50
        self.limit = 25


class GuardianTechScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.theguardian.com/technology/rss"
        self.source_name = "Guardian Tech"
        self.language = "EN"
        self.focus_topic = "Technology"
        self.daily_cap = 15
        self.limit = 25


class TechCrunchScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://techcrunch.com/feed/"
        self.source_name = "TechCrunch"
        self.language = "EN"
        self.focus_topic = "Technology"
        self.daily_cap = 25
        self.limit = 25


class HackerNewsScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://hnrss.org/frontpage"
        self.source_name = "Hacker News"
        self.language = "EN"
        self.focus_topic = "Technology"
        self.daily_cap = 45
        self.limit = 25


class TheVergeScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.theverge.com/rss/index.xml"
        self.source_name = "The Verge"
        self.language = "EN"
        self.focus_topic = "Technology"
        self.daily_cap = 25
        self.limit = 25


# ── Yeni Türkçe Kaynaklar (v1.8) ──────────────────────────────────────────────

class AnadoluAjansiScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.aa.com.tr/tr/rss/default?cat=guncel"
        self.source_name = "Anadolu Ajansı"
        self.language = "TR"
        self.focus_topic = None
        self.daily_cap = 70
        self.limit = 25


class AnadoluEkonomiScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"
        self.source_name = "AA Ekonomi"
        self.language = "TR"
        self.focus_topic = "Economy"
        self.daily_cap = 20
        self.limit = 25


# ── S2 (29 Eylül 2026): konu dengesi için eklenen kaynaklar ─────────────────────
# URL'ler 29 Eylül'de canlı doğrulandı (mock'lu testler feed geçerliliğini YAKALAMAZ).


class DunyaScraper(BaseRssScraper):
    def __init__(self):
        # Dünya Gazetesi — TR ekonomi
        self.url = "https://www.dunya.com/rss"
        self.source_name = "Dünya"
        self.limit = 25
        self.language = "TR"
        self.focus_topic = "Economy"
        self.daily_cap = 40


class CoinDeskScraper(BaseRssScraper):
    def __init__(self):
        # kripto/finans
        self.url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        self.source_name = "CoinDesk"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "Crypto"
        self.daily_cap = 20


class CointelegraphScraper(BaseRssScraper):
    def __init__(self):
        # kripto; yerel Windows TLS hatası verir, prod IP'den 200 (29 Eyl 2026 doğrulandı)
        self.url = "https://cointelegraph.com/rss"
        self.source_name = "Cointelegraph"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "Crypto"
        self.daily_cap = 20


class ScienceDailyScraper(BaseRssScraper):
    def __init__(self):
        # bilim/sağlık; 60 öğe, tarih sırasız
        self.url = "https://www.sciencedaily.com/rss/all.xml"
        self.source_name = "ScienceDaily"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "Science"
        self.daily_cap = 12


class AABilimTeknolojiScraper(BaseRssScraper):
    def __init__(self):
        # TR bilim
        self.url = "https://www.aa.com.tr/tr/rss/default?cat=bilim-teknoloji"
        self.source_name = "AA Bilim-Teknoloji"
        self.limit = 25
        self.language = "TR"
        self.focus_topic = "Science"
        self.daily_cap = 20


class AAKulturScraper(BaseRssScraper):
    def __init__(self):
        # TR kültür-sanat
        self.url = "https://www.aa.com.tr/tr/rss/default?cat=kultur"
        self.source_name = "AA Kültür"
        self.limit = 25
        self.language = "TR"
        self.focus_topic = "Culture"
        self.daily_cap = 15


class AlJazeeraScraper(BaseRssScraper):
    def __init__(self):
        # dünya
        self.url = "https://www.aljazeera.com/xml/rss/all.xml"
        self.source_name = "Al Jazeera"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "World"
        self.daily_cap = 30


class DWScraper(BaseRssScraper):
    def __init__(self):
        # dünya; 134 öğe, ~700 saatlik aralık — tarih sıralaması şart
        self.url = "https://rss.dw.com/xml/rss-en-all"
        self.source_name = "DW"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "World"
        self.daily_cap = 25


class BBCHealthScraper(BaseRssScraper):
    def __init__(self):
        # sağlık; 52 öğe, tarih sırasız
        self.url = "https://feeds.bbci.co.uk/news/health/rss.xml"
        self.source_name = "BBC Health"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "Health"
        self.daily_cap = 12


class BBCEntertainmentScraper(BaseRssScraper):
    def __init__(self):
        # eğlence/sanat
        self.url = "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"
        self.source_name = "BBC Entertainment"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "Entertainment"
        self.daily_cap = 12


class BBCScienceEnvironmentScraper(BaseRssScraper):
    def __init__(self):
        # çevre/iklim; 42 öğe, tarih sırasız
        self.url = "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"
        self.source_name = "BBC Science & Environment"
        self.limit = 25
        self.language = "EN"
        self.focus_topic = "Environment"
        self.daily_cap = 8
