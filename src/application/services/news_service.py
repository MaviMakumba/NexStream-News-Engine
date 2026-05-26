import asyncio
import logging
import re
from collections import Counter
from src.domain.ports.news_repository_port import NewsRepositoryPort
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article
from src.adapters.api.metrics import articles_processed_total
from typing import List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from src.domain.ports.email_port import EmailPort
    from src.domain.ports.subscriber_port import SubscriberRepositoryPort

logger = logging.getLogger(__name__)

# Hybrid search ağırlıkları
_FIELD_WEIGHTS = {"title": 0.9, "summary": 0.7, "content": 0.5}

# Turkish nominal suffixes ordered longest-first so we always strip the longest match.
# Enables queries like "beşiktaşın hocası" to match articles containing "beşiktaş hocası".
_TR_SUFFIXES = (
    "larından", "lerinden",
    "lardan", "lerden", "larla", "lerle",
    "larda", "lerde", "lara", "lere", "ların", "lerin",
    "ından", "inden", "undan", "ünden",
    "ları", "leri",
    "ndan", "nden", "ında", "inde", "unda", "ünde",
    "lar", "ler",
    "nda", "nde", "nın", "nin", "nun", "nün",
    "ına", "ine", "una", "üne",
    "ını", "ini", "unu", "ünü",
    "dan", "den", "tan", "ten",
    "yla", "yle",
    "nı", "ni", "nu", "nü",
    "na", "ne",
    "ya", "ye", "yı", "yi", "yu", "yü",
    "da", "de", "ta", "te",
    "la", "le",
    "li", "lı", "lu", "lü",
    "sı", "si", "su", "sü",
    "ın", "in", "un", "ün",
    "ı", "i", "u", "ü",
)
_DOUBLE_HIT_BONUS = 0.10
_CANDIDATE_MULTIPLIER = 3
_MIN_CANDIDATES = 20
_MAX_CANDIDATES = 50


class NewsService:

    def __init__(
        self,
        repository: NewsRepositoryPort,
        analyzer: AnalysisPort,
        search_repository=None,
        subscriber_repository: Optional["SubscriberRepositoryPort"] = None,
        email_port: Optional["EmailPort"] = None,
    ):
        self.repository = repository
        self.analyzer = analyzer
        self.search_repository = search_repository
        self.subscriber_repository = subscriber_repository
        self.email_port = email_port

    async def update_news_from_source(self, scraper: NewsScraperPort):
        logger.info("Güncelleme başladı: %s", scraper.__class__.__name__)
        articles: List[Article] = await scraper.fetch_news()

        # Bulk duplicate check — tek SQL sorgusu, N+1 elimine edildi
        existing_urls = self.repository.bulk_exists([a.url for a in articles])
        new_articles = [a for a in articles if a.url not in existing_urls]
        logger.info("%s: %d/%d yeni haber analiz edilecek", scraper.__class__.__name__, len(new_articles), len(articles))

        saved_count = 0
        loop = asyncio.get_running_loop()
        for i, article in enumerate(new_articles):
            if i > 0:
                await asyncio.sleep(2)
            result = await loop.run_in_executor(None, self.analyzer.analyze_text, article.content)

            article.summary = result["summary"]
            article.sentiment_score = result["sentiment_score"]
            article.sentiment_label = result["sentiment_label"]
            article.entities = result.get("entities")
            article.topic = result.get("topic", "Other")

            if self.search_repository:
                try:
                    article.is_duplicate = self.search_repository.is_near_duplicate(article)
                except Exception as e:
                    logger.warning("Dedup kontrolü başarısız, devam ediliyor: %s", e)

            saved = self.repository.save_article(article)
            if saved:
                saved_count += 1
                articles_processed_total.labels(source=article.source, status="saved").inc()
                if self.search_repository and article.id:
                    try:
                        self.search_repository.index_article(article)
                    except Exception as e:
                        logger.error("ChromaDB index hatası (PostgreSQL etkilenmedi): %s", e)
                if self.subscriber_repository and self.email_port:
                    try:
                        self._send_keyword_alerts(article)
                    except Exception as e:
                        logger.warning("Keyword alert hatası: %s", e)
            else:
                articles_processed_total.labels(source=article.source, status="duplicate").inc()

        logger.info("Güncelleme bitti: %d/%d haber kaydedildi", saved_count, len(new_articles))

    def list_news(self, limit: int = 10, sentiment: Optional[str] = None) -> List[Article]:
        return self.repository.get_latest_news(limit, sentiment)

    def hybrid_search(self, query: str, n_results: int = 10, source: str = None, sentiment: str = None) -> list[dict]:
        candidate_size = min(max(n_results * _CANDIDATE_MULTIPLIER, _MIN_CANDIDATES), _MAX_CANDIDATES)
        query_terms = self._tokenize(query)  # includes Turkish stems for better recall

        semantic_by_id: dict = {}
        if self.search_repository:
            try:
                for r in self.search_repository.search(query, candidate_size, source, sentiment):
                    semantic_by_id[r["id"]] = r
            except Exception as e:
                logger.error(f"Semantik arama hatası: {e}")

        try:
            keyword_articles = self.repository.keyword_search(
                query, candidate_size, source, sentiment, terms=query_terms
            )
        except Exception as e:
            logger.error(f"Keyword arama hatası: {e}")
            keyword_articles = []
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
    def _stem_tr(word: str) -> str:
        for suffix in _TR_SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[:-len(suffix)]
        return word

    @staticmethod
    def _tokenize(query: str) -> List[str]:
        tokens = [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 2]
        seen: set = set(tokens)
        expanded = list(tokens)
        for t in tokens:
            stem = NewsService._stem_tr(t)
            if stem != t and stem not in seen:
                seen.add(stem)
                expanded.append(stem)
        return expanded

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

    def get_trending(self, hours: int = 6, limit: int = 10) -> dict:
        articles = self.repository.get_recent_articles_with_entities(hours)
        entity_counter: Counter = Counter()
        entity_type_map: dict[str, str] = {}
        entity_titles: dict[str, list[str]] = {}

        for article in articles:
            if not article.entities:
                continue
            for etype, names in article.entities.items():
                if not isinstance(names, list):
                    continue
                singular = etype.rstrip("s")
                for name in names:
                    if not isinstance(name, str) or len(name) < 2:
                        continue
                    key = name.strip()
                    entity_counter[key] += 1
                    entity_type_map.setdefault(key, singular)
                    titles = entity_titles.setdefault(key, [])
                    if article.title not in titles and len(titles) < 3:
                        titles.append(article.title)

        top = entity_counter.most_common(limit)
        return {
            "hours": hours,
            "entities": [
                {
                    "name": name,
                    "count": count,
                    "type": entity_type_map[name],
                    "example_titles": entity_titles[name],
                }
                for name, count in top
            ],
        }

    def _send_keyword_alerts(self, article: Article) -> None:
        if self.subscriber_repository is None or self.email_port is None:
            return
        text = f"{article.title} {article.summary or ''} {article.content[:500]}".lower()
        for sub in self.subscriber_repository.get_active_subscribers():
            if sub.frequency != "instant" or not sub.keywords:
                continue
            for kw in sub.keywords:
                if kw.lower() in text:
                    self.email_port.send_alert(sub.email, article, kw)
                    break  # one alert per article per subscriber

    def list_news_paginated(self, limit: int, before_id: Optional[int] = None, source: Optional[str] = None, sentiment: Optional[str] = None, topic: Optional[str] = None) -> List[Article]:
        return self.repository.get_news_paginated(limit, before_id, source, sentiment, topic)

    def reanalyze_missed(self, limit: int = 5) -> int:
        articles = self.repository.get_unanalyzed_articles(limit)
        updated = 0
        for article in articles:
            try:
                result = self.analyzer.analyze_text(article.content)
                article.summary = result["summary"]
                article.sentiment_score = result["sentiment_score"]
                article.sentiment_label = result["sentiment_label"]
                article.entities = result.get("entities")
                article.topic = result.get("topic", "Other")
                if self.repository.update_article_analysis(article):
                    updated += 1
                    if self.search_repository and article.id:
                        try:
                            self.search_repository.index_article(article)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("Reanalyze missed hatası (id=%s): %s", article.id, e)
        if updated:
            logger.info("Reanalyze missed: %d/%d haber güncellendi", updated, len(articles))
        return updated

    def reanalyze_all(self) -> dict:
        articles = self.repository.get_all_articles()
        updated, failed, skipped = 0, 0, 0
        for article in articles:
            if article.entities is not None:
                skipped += 1
                continue
            try:
                result = self.analyzer.analyze_text(article.content)
                article.summary = result["summary"]
                article.sentiment_score = result["sentiment_score"]
                article.sentiment_label = result["sentiment_label"]
                article.entities = result.get("entities")
                article.topic = result.get("topic", "Other")

                if self.repository.update_article_analysis(article):
                    updated += 1
                    if self.search_repository and article.id:
                        try:
                            self.search_repository.index_article(article)
                        except Exception:
                            pass
                else:
                    failed += 1
            except Exception as e:
                logger.error("Reanalyze hatası (id=%s): %s", article.id, e)
                failed += 1
        return {"total": len(articles), "updated": updated, "skipped": skipped, "failed": failed}

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