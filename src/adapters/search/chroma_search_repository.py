"""ChromaDB vektör arama adapter'ı — indexleme, semantik arama ve near-duplicate tespiti.

Skor formülü: 1/(1+distance) → (0,1] aralığına normalize. Dedup eşiği 0.92:
yeni haber mevcut bir vektöre bu kadar yakınsa is_duplicate işaretlenir.
"""

import logging
import chromadb
from src.domain.models.article import Article
from src.adapters.search.embedder_factory import build_embedder
from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "news_articles"


class ChromaSearchRepository:

    # Retention taramasının sayfa boyutu — bkz. _collect_stale_ids.
    RETENTION_SCAN_BATCH = 1000

    def __init__(self, embedder: EmbeddingPort = None):
        # Varsayılan factory'den gelir (HTTP servisi). Somut sınıf DEĞİL port
        # tip ipucu: bu sınıf hangi embedder olduğunu bilmemeli.
        self.embedder = embedder or build_embedder()
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
            published = article.published_at or article.created_at
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
                    "published_at": published.isoformat() if published else "",
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

    def find_similar(self, article_id: int, n_results: int = 6, threshold: float = 0.72) -> list[dict]:
        """Aynı story cluster'daki diğer kaynakları bulur (v2.2, "bu haberi kim
        nasıl anlatıyor" görünümü — rakip taraması, Ground News Blindspot'unun
        küçük ölçekli hali).

        `is_near_duplicate`'in eşiği (0.92) kelimesi kelimesine aynı haberi
        yakalar; burada daha gevşek bir eşik farklı kaynakların AYNI OLAYI
        farklı kelimelerle anlattığı makaleleri de kapsar. Zaten indexlenmiş
        vektörü tekrar embed ETMEZ — `collection.get` ile saklı embedding'i
        okur, embedder servisine gereksiz bir HTTP çağrısı atmaz.
        """
        try:
            existing = self.collection.get(ids=[str(article_id)], include=["embeddings"])
            if len(existing["ids"]) == 0:
                return []
            embedding = existing["embeddings"][0]
            results = self.collection.query(query_embeddings=[embedding], n_results=n_results + 1)
            items = []
            for i, doc_id in enumerate(results["ids"][0]):
                if doc_id == str(article_id):
                    continue
                distance = results["distances"][0][i]
                similarity = 1 / (1 + distance)
                if similarity < threshold:
                    continue
                meta = results["metadatas"][0][i]
                items.append({
                    "id": int(doc_id),
                    "title": meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "url": meta.get("url", ""),
                    "score": round(similarity, 4),
                })
                if len(items) >= n_results:
                    break
            return items
        except Exception as e:
            logger.warning("Story cluster sorgusu başarısız: %s", e)
            return []

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
                    "published_at": meta.get("published_at", ""),
                })
            return items
        except Exception as e:
            logger.error("ChromaDB arama hatası: %s", e)
            return []

    def delete_before(self, cutoff_iso: str) -> int:
        """Belirtilen ISO tarihinden eski vektörleri koleksiyondan kaldırır.

        Postgres'e dokunmaz — geri dönüşü `reindex_all()` ile mümkündür.

        NEDEN `where={"published_at": {"$lt": ...}}` DEĞİL: ChromaDB `$lt`
        operatörünü yalnızca int/float için kabul eder, ISO tarih string'i
        verilince `ValueError` fırlatır. Eski kod bunu yapıyor, hata da
        aşağıdaki `except`'te yutuluyordu — retention job'ı her gece sessizce
        0 vektör siliyordu (29 Tem 2026'da gerçek ChromaDB'ye karşı yakalandı;
        mock'lu test geçersiz `where`'i sorunsuz kabul ettiği için gizlenmişti).
        Doğru yol: metadata taranır, eskiler Python'da seçilir, id ile silinir.
        """
        try:
            stale = self._collect_stale_ids(cutoff_iso)
            if not stale:
                logger.info("ChromaDB retention: silinecek vektör yok (cutoff=%s)", cutoff_iso)
                return 0
            self.collection.delete(ids=stale)
            logger.info("ChromaDB retention: %d vektör silindi (cutoff=%s)", len(stale), cutoff_iso)
            return len(stale)
        except Exception as e:
            logger.error("ChromaDB retention silme hatası: %s", e)
            return 0

    def _collect_stale_ids(self, cutoff_iso: str) -> list[str]:
        """Cutoff'tan eski vektörlerin id'lerini sayfalayarak toplar.

        Koleksiyon tek seferde çekilmez: t3.small'da (1.9GB RAM) on binlerce
        metadata kaydını aynı anda belleğe almak istemiyoruz.

        `published_at` boş olan vektörler ATLANIR — boş string her cutoff'tan
        küçük sayılır ve tarihi bilinmeyen her vektör sessizce silinirdi.
        """
        stale: list[str] = []
        offset = 0
        while True:
            page = self.collection.get(
                include=["metadatas"], limit=self.RETENTION_SCAN_BATCH, offset=offset
            )
            ids = page.get("ids") or []
            if not ids:
                break
            metadatas = page.get("metadatas") or []
            for doc_id, meta in zip(ids, metadatas):
                published_at = (meta or {}).get("published_at") or ""
                if published_at and published_at < cutoff_iso:
                    stale.append(doc_id)
            if len(ids) < self.RETENTION_SCAN_BATCH:
                break
            offset += len(ids)
        return stale

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
