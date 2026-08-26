"""Analyzer + sorgu genişletme kompozisyon noktası — Groq birincil, HuggingFace opsiyonel yedek."""
import logging
from typing import Optional
from src.adapters.analysis.groq_analyzer import GroqAnalyzer
from src.adapters.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from src.adapters.analysis.fallback_analyzer import FallbackAnalyzer
from src.adapters.analysis.groq_query_expander import GroqQueryExpander
from src.adapters.analysis.caching_query_expander import CachingQueryExpander
from src.adapters.analysis.groq_question_answerer import GroqQuestionAnswerer
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.domain.ports.question_answering_port import QuestionAnsweringPort
from src.domain.ports.cache_port import CachePort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# build_query_expander istek başına çağrıldığı için (dependencies.get_news_service),
# cache'siz ortamda her istekte log basmasın diye uyarı bir kez verilir.
_no_cache_warning_logged = False


def build_analyzer() -> AnalysisPort:
    analyzers = [GroqAnalyzer()]
    if settings.huggingface_api_key:
        analyzers.append(HuggingFaceAnalyzer())
    return FallbackAnalyzer(analyzers)


def build_query_expander(cache: CachePort) -> Optional[QueryExpansionPort]:
    """Sorgu genişletme kompozisyon noktası. `cache` dışarıdan verilir —
    dependencies.py'deki tekil CachePort singleton'ı paylaşılsın diye
    (kendi cache'ini yaratırsa tekillik bozulur)."""
    global _no_cache_warning_logged
    if not settings.search_query_expansion_enabled:
        return None

    # Kota güvenliği: `build_cache()` REDIS_URL boşsa NullCacheAdapter döner —
    # get()/set() no-op'tur, yani CachingQueryExpander hiçbir şey cache'lemez ve
    # /search üzerindeki HER benzersiz sorgu doğrudan Groq'a gider. Arama public
    # ve anonim (sadece rate-limited, kota YOK), GROQ_API_KEY ise haber analiz
    # worker'ı ile PAYLAŞILIYOR — cache'siz genişletme, analiz hattının günlük
    # kotasını yakabilir. Prod'da REDIS_URL zaten dolu (limiter storage'ı da onu
    # kullanıyor), bu yüzden bu dal sadece Redis'siz dev/lokal ortamı kapsar.
    if not settings.redis_url:
        if not _no_cache_warning_logged:
            logger.warning(
                "Sorgu genişletme devre dışı: REDIS_URL boş (cache yok). "
                "Cache olmadan her arama Groq'a gider ve analiz hattıyla paylaşılan "
                "kotayı tüketir. Açmak için REDIS_URL ayarla."
            )
            _no_cache_warning_logged = True
        return None

    return CachingQueryExpander(GroqQueryExpander(), cache)


def build_question_answerer() -> QuestionAnsweringPort:
    """RAG soru-cevap kompozisyon noktası. Tek implementasyon var (Groq) —
    HuggingFace'in Q&A karşılığı yok, build_analyzer()'daki fallback zinciri
    YOK (YAGNI, bkz. spec 'Mimari & Bileşenler')."""
    return GroqQuestionAnswerer()
