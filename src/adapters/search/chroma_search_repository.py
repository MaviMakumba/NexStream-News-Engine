"""ChromaDB vektör arama adapter'ı — indexleme, semantik arama ve near-duplicate tespiti.

Skor formülü: 1/(1+distance) → (0,1] aralığına normalize. Dedup eşiği 0.92:
yeni haber mevcut bir vektöre bu kadar yakınsa is_duplicate işaretlenir.
"""

import logging
import chromadb
from src.domain.models.article import Article
from src.adapters.search.sentence_transformer_embedder import SentenceTransformerEmbedder
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "news_articles"


class ChromaSearchRepository:

    def __init__(self, embedder: SentenceTransformerEmbedder = None):
        self.embedder = embedder or SentenceTransformerEmbedder()
        self.client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self.collection = self.client.get_or_create_collection(COLLECTION_NAME)

    def _article_embedding_text(self, article: Article) -> str:
        return f"{article.title}. {article.summary or article.content[:200]}"

    def index_article(self, article: Article) -> bool:
        if not article.id:
            logger.warning("index_article: article.id yok, atlanıyor.")
            return False
        try:
            text = self._article_embedding_text(article)
            embedding = self.embedder.embed_text(text)
            self.collection.upsert(
                ids=[str(article.id)],
                embeddings=[embedding],
                metadatas=[{
                    "title": article.title,
                    "source": article.source,
                    "url": article.url,
                    "summary": article.summary or "",
                    "sentiment_label": article.sentiment_label or "",
                    "topic": article.topic or "",
                }],
            )
            return True
        except Exception as e:
            logger.error("ChromaDB index hatası: %s", e)
            return False

    def is_near_duplicate(self, article: Article, threshold: float = 0.92) -> bool:
        try:
            if self.collection.count() == 0:
                return False
            text = self._article_embedding_text(article)
            embedding = self.embedder.embed_text(text)
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=1,
            )
            if not results["ids"][0]:
                return False
            distance = results["distances"][0][0]
            similarity = 1 / (1 + distance)
            return similarity >= threshold
        except Exception as e:
            logger.warning("Dedup sorgusu başarısız: %s", e)
            return False

    def search(self, query: str, n_results: int = 10, source: str = None, sentiment: str = None) -> list[dict]:
        try:
            embedding = self.embedder.embed_text(query)
            where = self._build_where(source, sentiment)
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=where,
            )
            items = []
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                items.append({
                    "id": doc_id,
                    "title": meta.get("title", ""),
                    "summary": meta.get("summary", ""),
                    "source": meta.get("source", ""),
                    "url": meta.get("url", ""),
                    "score": round(1 / (1 + distance), 4),
                })
            return items
        except Exception as e:
            logger.error("ChromaDB arama hatası: %s", e)
            return []

    @staticmethod
    def _build_where(source: str = None, sentiment: str = None) -> dict | None:
        conditions = []
        if source:
            conditions.append({"source": {"$eq": source}})
        if sentiment:
            conditions.append({"sentiment_label": {"$eq": sentiment}})
        if len(conditions) == 0:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}
