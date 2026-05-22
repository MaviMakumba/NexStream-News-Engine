import logging
from src.domain.ports.news_repository_port import NewsRepositoryPort
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article
from typing import List, Optional

logger = logging.getLogger(__name__)


class NewsService:

    def __init__(self, repository: NewsRepositoryPort, analyzer: AnalysisPort, search_repository=None):
        self.repository = repository
        self.analyzer = analyzer
        self.search_repository = search_repository

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

            saved = self.repository.save_article(article)
            if saved:
                saved_count += 1
                if self.search_repository and article.id:
                    try:
                        self.search_repository.index_article(article)
                    except Exception as e:
                        logger.error(f"ChromaDB index hatası (PostgreSQL etkilenmedi): {e}")

        print(f"--- BİTTİ: {saved_count}/{len(articles)} haber kaydedildi ---")

    def list_news(self, limit: int = 10, sentiment: Optional[str] = None) -> List[Article]:
        return self.repository.get_latest_news(limit, sentiment)

    def hybrid_search(self, query: str, n_results: int = 10, source: str = None, sentiment: str = None) -> list[dict]:
        semantic_results = []
        if self.search_repository:
            try:
                semantic_results = self.search_repository.search(query, n_results, source, sentiment)
            except Exception as e:
                logger.error(f"Semantik arama hatası: {e}")

        try:
            keyword_articles = self.repository.keyword_search(query, n_results, source, sentiment)
        except Exception as e:
            logger.error(f"Keyword arama hatası: {e}")
            keyword_articles = []

        seen_ids = {r["id"] for r in semantic_results}
        for article in keyword_articles:
            if str(article.id) not in seen_ids:
                semantic_results.append({
                    "id": str(article.id),
                    "title": article.title,
                    "summary": article.summary or "",
                    "source": article.source,
                    "url": article.url,
                    "score": 0.0,
                })

        return semantic_results[:n_results]

    def reindex_all(self) -> dict:
        if not self.search_repository:
            return {"indexed": 0, "error": "ChromaDB bağlı değil"}
        articles = self.repository.get_all_articles()
        indexed, failed = 0, 0
        for article in articles:
            try:
                if self.search_repository.index_article(article):
                    indexed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Reindex hatası (id={article.id}): {e}")
                failed += 1
        return {"total": len(articles), "indexed": indexed, "failed": failed}