import logging
import re
from src.domain.ports.news_repository_port import NewsRepositoryPort
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article
from typing import List, Optional

logger = logging.getLogger(__name__)

# Hybrid search ağırlıkları
_FIELD_WEIGHTS = {"title": 0.9, "summary": 0.7, "content": 0.5}
_DOUBLE_HIT_BONUS = 0.10
_CANDIDATE_MULTIPLIER = 3
_MIN_CANDIDATES = 20
_MAX_CANDIDATES = 50


class NewsService:

    def __init__(self, repository: NewsRepositoryPort, analyzer: AnalysisPort, search_repository=None):
        self.repository = repository
        self.analyzer = analyzer
        self.search_repository = search_repository

    def update_news_from_source(self, scraper: NewsScraperPort):
        logger.info("Güncelleme başladı: %s", scraper.__class__.__name__)
        articles: List[Article] = scraper.fetch_news()
        saved_count = 0

        for article in articles:
            logger.info("Analiz ediliyor: %s", article.title[:60])
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
                        logger.error("ChromaDB index hatası (PostgreSQL etkilenmedi): %s", e)

        logger.info("Güncelleme bitti: %d/%d haber kaydedildi", saved_count, len(articles))

    def list_news(self, limit: int = 10, sentiment: Optional[str] = None) -> List[Article]:
        return self.repository.get_latest_news(limit, sentiment)

    def hybrid_search(self, query: str, n_results: int = 10, source: str = None, sentiment: str = None) -> list[dict]:
        candidate_size = min(max(n_results * _CANDIDATE_MULTIPLIER, _MIN_CANDIDATES), _MAX_CANDIDATES)

        semantic_by_id: dict = {}
        if self.search_repository:
            try:
                for r in self.search_repository.search(query, candidate_size, source, sentiment):
                    semantic_by_id[r["id"]] = r
            except Exception as e:
                logger.error(f"Semantik arama hatası: {e}")

        try:
            keyword_articles = self.repository.keyword_search(query, candidate_size, source, sentiment)
        except Exception as e:
            logger.error(f"Keyword arama hatası: {e}")
            keyword_articles = []

        query_terms = self._tokenize(query)
        keyword_by_id: dict = {}
        for article in keyword_articles:
            relevance = self._keyword_relevance(article, query_terms)
            if relevance > 0:
                keyword_by_id[str(article.id)] = (relevance, article)

        combined = []
        for article_id in set(semantic_by_id) | set(keyword_by_id):
            sem_score = semantic_by_id[article_id]["score"] if article_id in semantic_by_id else 0.0
            kw_score = keyword_by_id[article_id][0] if article_id in keyword_by_id else 0.0

            base = max(sem_score, kw_score)
            bonus = _DOUBLE_HIT_BONUS if (article_id in semantic_by_id and article_id in keyword_by_id) else 0.0
            final = min(round(base + bonus, 4), 1.0)

            if article_id in semantic_by_id:
                data = dict(semantic_by_id[article_id])
            else:
                article = keyword_by_id[article_id][1]
                data = {
                    "id": article_id,
                    "title": article.title,
                    "summary": article.summary or "",
                    "source": article.source,
                    "url": article.url,
                }
            data["score"] = final
            combined.append(data)

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:n_results]

    @staticmethod
    def _tokenize(query: str) -> List[str]:
        return [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 2]

    @staticmethod
    def _keyword_relevance(article: Article, query_terms: List[str]) -> float:
        if not query_terms:
            return 0.0

        title = article.title.lower() if article.title else ""
        summary = article.summary.lower() if article.summary else ""
        content = article.content.lower() if article.content else ""

        n = len(query_terms)
        title_hits = sum(1 for t in query_terms if t in title)
        summary_hits = sum(1 for t in query_terms if t in summary)
        content_hits = sum(1 for t in query_terms if t in content)

        title_score = (title_hits / n) * _FIELD_WEIGHTS["title"]
        summary_score = (summary_hits / n) * _FIELD_WEIGHTS["summary"]
        content_score = (content_hits / n) * _FIELD_WEIGHTS["content"]

        return round(max(title_score, summary_score, content_score), 4)

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