import os
import logging
import chromadb
from src.domain.models.article import Article
from src.adapters.search.sentence_transformer_embedder import SentenceTransformerEmbedder

logger = logging.getLogger(__name__)

COLLECTION_NAME = "news_articles"


class ChromaSearchRepository:

    def __init__(self, embedder: SentenceTransformerEmbedder = None):
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8001"))
        self.embedder = embedder or SentenceTransformerEmbedder()
        self.client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(COLLECTION_NAME)

    def index_article(self, article: Article) -> bool:
        if not article.id:
            logger.warning("index_article: article.id yok, atlanıyor.")
            return False
        try:
            text = f"{article.title}. {article.summary or article.content[:200]}"
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
                }],
            )
            return True
        except Exception as e:
            logger.error(f"ChromaDB index hatası: {e}")
            return False

    def search(self, query: str, n_results: int = 10) -> list[dict]:
        try:
            embedding = self.embedder.embed_text(query)
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
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
                    "score": round(1 - distance, 4),
                })
            return items
        except Exception as e:
            logger.error(f"ChromaDB arama hatası: {e}")
            return []
