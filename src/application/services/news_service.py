from src.domain.ports.scraper_port import NewsScraperPort
from src.adapters.repositories.news_repository import NewsRepository
# Yeni Analiz Servisini çağırıyoruz (Henüz klasör yapın tam oturmadığı için relative import yapabilirsin)
# Veya direkt bu dosyanın içine AnalysisService class'ını da koyabilirsin şimdilik.
# Ama doğrusu import etmektir:
from src.domain.services.analysis_service import AnalysisService

class NewsService:
    def __init__(self, repository: NewsRepository):
        # Servis, hangi depoyu kullanacağını bilir (Dependency Injection)
        self.repository = repository
        # Analiz servisini başlat
        self.analyzer = AnalysisService()

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
            # 1. Önce Yapay Zeka ile Analiz Et
            print(f"🧠 Analiz ediliyor: {article['title'][:30]}...")
            analysis_result = self.analyzer.analyze_text(article['content'])
            
            # 2. Analiz sonuçlarını haber verisine ekle
            article["summary"] = analysis_result["summary"]
            article["sentiment_score"] = analysis_result["sentiment_score"]
            article["sentiment_label"] = analysis_result["sentiment_label"]
            
            # 3. Veritabanına Kaydet (Repository'nin de bu yeni alanları kabul etmesi lazım*)
            # *Not: Repository'de NewsORM nesnesi oluştururken bu alanları da eklemeliyiz.
            # Şimdilik save_article metodunu da güncellememiz gerekecek.
            
            is_saved = self.repository.save_article(article)
            if is_saved:
                saved_count += 1
                
        print(f"--- İŞLEM BİTTİ: {saved_count} haber analiz edildi ve kaydedildi. ---\n")