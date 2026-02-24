import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from src.domain.ports.scraper_port import NewsScraperPort

class BBCRssScraper(NewsScraperPort):
    def __init__(self):
        # BBC'nin Teknoloji haberleri RSS adresi
        self.url = "http://feeds.bbci.co.uk/news/technology/rss.xml"
        self.source_name = "BBC Technology"

    def fetch_news(self) -> List[Dict]:
        print(f"📡 {self.source_name} kaynağına bağlanılıyor...")
        news_list = []
        
        try:
            # 1. İstek At (Request)
            # Timeout=10 sn ekliyoruz ki internet yoksa kod sonsuza kadar beklemesin
            response = requests.get(self.url, timeout=10)
            response.raise_for_status() # Hata varsa (Örn: 404 Sayfa Yok) işlemi durdur
            
            # 2. Gelen XML Verisini Parçala (Parse)
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all("item")
            
            print(f"✅ {len(items)} adet haber bulundu. İlk 5 tanesi alınıyor.")

            # 3. Veriyi Bizim Formatımıza Çevir (Mapping)
            # Sadece en güncel 5 haberi alıyoruz
            for item in items[:5]:
                title = item.find("title").text if item.find("title") else "Başlıksız"
                description = item.find("description").text if item.find("description") else "İçerik yok"
                link = item.find("link").text if item.find("link") else ""
                
                news_list.append({
                    "title": title,
                    "content": description,
                    "source": self.source_name,
                    "url": link
                })
                
            return news_list
            
        except Exception as e:
            print(f"❌ Hata oluştu: {e}")
            return []