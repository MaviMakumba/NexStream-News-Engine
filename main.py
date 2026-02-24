from src.adapters.repositories.news_repository import NewsRepository
from src.application.services.news_service import NewsService
from src.adapters.scrapers.bbc_scraper import BBCRssScraper

def main():
    # 1. Altyapıyı Hazırla (Dependency Injection)
    repo = NewsRepository()
    service = NewsService(repo)
    
    # 2. Robotları Hazırla (Şimdilik sadece BBC)
    bbc_bot = BBCRssScraper()
    
    # 3. Servisi Çalıştır
    service.update_news_from_source(bbc_bot)
    
    # 4. Temizlik
    repo.close()

if __name__ == "__main__":
    main()