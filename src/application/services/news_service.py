from src.domain.ports.news_repository_port import NewsRepositoryPort
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article
from typing import List, Optional

class NewsService:

    def __init__(self, repository: NewsRepositoryPort, analyzer: AnalysisPort):
        self.repository = repository
        self.analyzer = analyzer

    def update_news_from_source(self, scraper: NewsScraperPort):
        print(f"--- GÜNCELLEME: {scraper.__class__.__name__} ---")
        articles: List[Article] = scraper.fetch_news()
        saved_count = 0

        for article in articles:
            print(f"🧠 Analiz: {article.title[:40]}...")
            result = self.analyzer.analyze_text(article.content)

            article.summary = result["summary"]
            article.sentiment_score = result["sentiment_score"]
            article.sentiment_label = result["sentiment_label"]

            if self.repository.save_article(article):
                saved_count += 1

        print(f"--- BİTTİ: {saved_count}/{len(articles)} haber kaydedildi ---")

    def list_news(self, limit: int = 10, sentiment: Optional[str] = None) -> List[Article]:
        return self.repository.get_latest_news(limit, sentiment)