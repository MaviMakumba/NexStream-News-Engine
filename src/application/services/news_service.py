from src.domain.ports.scraper_port import NewsScraperPort
from src.adapters.repositories.news_repository import NewsRepository

class NewsService:
    def __init__(self, repository: NewsRepository):
        # Servis, hangi depoyu kullanacağını bilir (Dependency Injection)
        self.repository = repository

    def update_news_from_source(self, scraper: NewsScraperPort):
        """
        Verilen robottan (scraper) haberleri çeker ve depoya kaydeder.
        """
        print(f"--- GÜNCELLEME BAŞLADI: {scraper.__class__.__name__} ---")
        
        # 1. Robottan veriyi çek
        articles = scraper.fetch_news()
        
        # 2. Her haberi tek tek kaydet
        saved_count = 0
        for article in articles:
            is_saved = self.repository.save_article(article)
            if is_saved:
                saved_count += 1
                
        print(f"--- İŞLEM BİTTİ: {len(articles)} haberden {saved_count} tanesi yeni kaydedildi. ---\n")