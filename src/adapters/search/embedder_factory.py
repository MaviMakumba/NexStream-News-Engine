"""Embedder kompozisyon noktası — `analysis/factory.py` desenini izler.

Varsayılan `http`: model ayrı serviste, tek kopya. `local` yalnızca Docker'sız
geliştirme içindir.

DİKKAT: `local` dalındaki import FONKSİYON İÇİNDE. `app`/`worker` image'larında
`sentence-transformers` KURULU DEĞİL — modül seviyesine taşınırsa o container'lar
açılışta ImportError ile çöker. Aynı gerekçeyle `billing_router.py::_require_stripe()`
de Stripe SDK'sını fonksiyon içinde import eder.
"""

from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings


def build_embedder() -> EmbeddingPort:
    """Ayarlara göre embedder kurar. Çağıran hangi implementasyon olduğunu bilmez."""
    if settings.embedder_mode == "local":
        from src.adapters.search.sentence_transformer_embedder import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder()

    from src.adapters.search.http_embedder import HttpEmbedderAdapter
    return HttpEmbedderAdapter()
