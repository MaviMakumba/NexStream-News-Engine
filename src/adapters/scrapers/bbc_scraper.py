import requests
from bs4 import BeautifulSoup
from typing import List
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article  # ✅ Eklendi

class BBCRssScraper(NewsScraperPort):
    def __init__(self):
        self.url = "http://feeds.bbci.co.uk/news/technology/rss.xml"
        self.source_name = "BBC Technology"

    def fetch_news(self) -> List[Article]:  # ✅ Dict → Article
        print(f"📡 {self.source_name} kaynağına bağlanılıyor...")
        articles = []

        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all("item")
            print(f"✅ {len(items)} haber bulundu. İlk {min(25, len(items))} alınıyor.")

            for item in items[:25]:  # İlk 25 haberle sınırla
                title = item.find("title").text if item.find("title") else "Başlıksız"
                content = item.find("description").text if item.find("description") else ""
                url = item.find("link").text if item.find("link") else ""

                articles.append(Article(  # ✅ Dict → Article objesi
                    title=title,
                    content=content,
                    source=self.source_name,
                    url=url,
                ))

            return articles

        except Exception as e:
            print(f"❌ Hata: {e}")
            return []