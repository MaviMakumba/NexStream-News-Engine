"""NewsService — uygulamanın orkestrasyon katmanı (hexagonal core).

Port'ları birbirine bağlar, iş akışlarını yürütür; HTTP/DB/LLM detayı bilmez:

    scrape akışı   : update_news_from_source → analiz → skorlama → kaydet → indexle
    arama          : hybrid_search (ChromaDB semantik + PostgreSQL keyword birleşimi)
    keşif          : get_trending (entity agregasyonu), get_related (entity overlap)
    bakım          : reanalyze_missed/reanalyze_all (eksik analizleri tamamlar),
                     reindex_all (ChromaDB'yi sıfırdan doldurur)

Hata felsefesi: tekil haber/adapter hatası akışı durdurmaz — logla, atla, devam et.
"""

import asyncio
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from src.domain.ports.news_repository_port import NewsRepositoryPort
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.scraper_port import NewsScraperPort
from src.domain.models.article import Article
from src.domain.scoring.quality import compute_quality_score
from src.domain.scoring.credibility import base_credibility, compute_credibility
from src.domain.services.subscriber_matching import matched_keyword
from src.adapters.api.metrics import articles_processed_total
from src.infrastructure.config.settings import settings
from typing import List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from src.domain.ports.email_port import EmailPort
    from src.domain.ports.subscriber_port import SubscriberRepositoryPort
    from src.domain.ports.query_expansion_port import QueryExpansionPort

logger = logging.getLogger(__name__)

# Hybrid search alan ağırlıkları: başlık eşleşmesi içerik eşleşmesinden değerlidir.
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
# Hem semantik hem keyword aramada çıkan sonuç daha güvenilirdir → küçük bonus.
_DOUBLE_HIT_BONUS = 0.10
# LLM sorgu genişletmesinden gelen ikincil terimlerin skor ağırlığı — asıl
# (birincil) eşleşmeyi asla domine etmesin diye 1.0'ın belirgin altında.
_EXPANSION_WEIGHT = 0.4
# Aday havuzu istenenden geniş tutulur ki birleştirme sonrası sıralama sağlıklı olsun.
_CANDIDATE_MULTIPLIER = 3
_MIN_CANDIDATES = 20
_MAX_CANDIDATES = 50


class NewsService:
    """Haber iş akışlarının orkestratörü — tüm bağımlılıklar port olarak enjekte edilir.

    search_repository / subscriber_repository / email_port opsiyoneldir:
    verilmezse ilgili özellik (semantik arama, keyword alert) sessizce devre dışı kalır.
    """

    def __init__(
        self,
        repository: NewsRepositoryPort,
        analyzer: AnalysisPort,
        search_repository=None,
        subscriber_repository: Optional["SubscriberRepositoryPort"] = None,
        email_port: Optional["EmailPort"] = None,
        query_expander: Optional["QueryExpansionPort"] = None,
    ):
        self.repository = repository
        self.analyzer = analyzer
        self.search_repository = search_repository
        self.subscriber_repository = subscriber_repository
        self.email_port = email_port
        self.query_expander = query_expander

    @staticmethod
    def _apply_analysis(article: Article, result: dict) -> None:
        """LLM analiz sonucunu (sentiment + NER + topic) makaleye işler.

        Scrape, reanalyze_missed ve reanalyze_all aynı eşlemeyi paylaşır —
        yeni bir analiz alanı eklendiğinde sadece burası değişir.
        """
        article.summary = result["summary"]
        article.sentiment_score = result["sentiment_score"]
        article.sentiment_label = result["sentiment_label"]
        article.entities = result.get("entities")
        article.topic = result.get("topic", "Other")

    async def update_news_from_source(self, scraper: NewsScraperPort):
        """Tek kaynağı uçtan uca işler: çek → analiz et → skorla → kaydet → indexle.

        Groq rate limit'ini korumak için analizler sıralı ve 2sn aralıklı çalışır;
        ChromaDB/alert hataları kaydı engellemez (PostgreSQL tek doğruluk kaynağı).
        """
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
                await asyncio.sleep(2)  # Groq TPM limitini aşmamak için throttle
            result = await loop.run_in_executor(None, self.analyzer.analyze_text, article.content)
            self._apply_analysis(article, result)

            try:
                self._enrich_metadata(article)
            except Exception as e:
                logger.warning("Metadata zenginleştirme başarısız, devam ediliyor: %s", e)

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
        """Semantik (ChromaDB) ve keyword (PostgreSQL) aramayı birleştirir.

        Skor = (max(semantik, keyword) + double-hit bonus) * recency çarpanı
        (`_decay_factor` — bugün 1.0, `search_recency_window_days` sonra
        `search_recency_decay_floor`'a iner). Additive bonus yerine çarpımsal
        decay kullanılır: skor tavanına (1.0) takılan tam eşleşmeler artık
        tazelikten etkilenmeye devam eder, sadece toplama ile maskelenmez.
        Taraflardan biri hata verirse diğeri tek başına sonuç döndürür.

        `query_expander` (opsiyonel) — LLM ile ilişkili ek terimler üretir
        ("İstanbul" → "Beykoz"). SADECE keyword tarafına, düşük ağırlıkla
        (`_EXPANSION_WEIGHT`) eklenir; semantik taraf hiç etkilenmez (embedding
        sorgusunu genişletilmiş terimlerle şişirmek orijinal sorgunun anlamını
        sulandırma riski taşır). Genişletme başarısız olursa (exception/boş
        liste) arama sessizce orijinal sorguyla devam eder — bkz. spec
        "arama ilişkisel genişletme" (20 Ağu 2026).
        """
        candidate_size = min(max(n_results * _CANDIDATE_MULTIPLIER, _MIN_CANDIDATES), _MAX_CANDIDATES)
        query_terms = self._tokenize(query)  # includes Turkish stems for better recall (SQL adayı)
        relevance_terms = self._canonical_terms(query)  # coverage skoru için — bkz. docstring

        expanded_terms: List[str] = []
        if self.query_expander:
            try:
                expanded_terms = self.query_expander.expand(query)
            except Exception as e:
                logger.warning("Sorgu genişletme başarısız, orijinal sorguyla devam: %s", e)

        # Genişletilmiş terimler SQL aday havuzuna da girer — yoksa o makale
        # DB'den hiç çekilmez, _keyword_relevance onu hiç göremez.
        sql_terms = query_terms + [t.lower() for t in expanded_terms if t]

        semantic_by_id: dict = {}
        if self.search_repository:
            try:
                for r in self.search_repository.search(query, candidate_size, source, sentiment):
                    semantic_by_id[r["id"]] = r
            except Exception as e:
                logger.error(f"Semantik arama hatası: {e}")

        try:
            keyword_articles = self.repository.keyword_search(
                query, candidate_size, source, sentiment, terms=sql_terms
            )
        except Exception as e:
            logger.error(f"Keyword arama hatası: {e}")
            keyword_articles = []
        keyword_by_id: dict = {}
        for article in keyword_articles:
            relevance = self._keyword_relevance(article, relevance_terms, secondary_terms=expanded_terms)
            if relevance > 0:
                keyword_by_id[str(article.id)] = (relevance, article)

        combined = []
        for article_id in set(semantic_by_id) | set(keyword_by_id):
            sem_score = semantic_by_id[article_id]["score"] if article_id in semantic_by_id else 0.0
            kw_score = keyword_by_id[article_id][0] if article_id in keyword_by_id else 0.0

            base = max(sem_score, kw_score)
            bonus = _DOUBLE_HIT_BONUS if (article_id in semantic_by_id and article_id in keyword_by_id) else 0.0

            if article_id in semantic_by_id:
                data = dict(semantic_by_id[article_id])
                data.pop("published_at", None)
            else:
                article = keyword_by_id[article_id][1]
                data = {
                    "id": article_id,
                    "title": article.title,
                    "summary": article.summary or "",
                    "source": article.source,
                    "url": article.url,
                }

            # Postgres verisi (keyword eşleşmesi) her zaman güncel/gerçek — tarih için tercih edilir.
            if article_id in keyword_by_id:
                kw_article = keyword_by_id[article_id][1]
                date_value = kw_article.published_at or kw_article.created_at
            else:
                date_value = semantic_by_id[article_id].get("published_at")

            relevance = min(round(base + bonus, 4), 1.0)
            recency = self._recency_factor(date_value)
            final = round(relevance * self._decay_factor(recency), 4)

            data["score"] = final
            data["created_at"] = date_value
            data["_recency_factor"] = recency
            combined.append(data)

        # Aynı (skor, tazelik) çiftine sahip sonuçlar için ikincil anahtar yine
        # tazelik — pratikte skor zaten decay ile ayrıştığından nadiren devreye girer.
        combined.sort(key=lambda x: (x["score"], x["_recency_factor"]), reverse=True)
        return combined[:n_results]

    @staticmethod
    def _decay_factor(recency: float) -> float:
        """Çarpımsal tazelik katsayısı: bugün → 1.0, pencere sonu → `search_recency_decay_floor`.

        Additive bonus'un aksine tavan skora (1.0) takılan tam eşleşmeleri de
        etkiler — relevance ile ÇARPILDIĞI için maskelenmez.
        """
        floor = settings.search_recency_decay_floor
        return floor + (1.0 - floor) * recency

    @staticmethod
    def _recency_factor(date_value) -> float:
        """Taze içerik oranı: bugün → 1.0, `search_recency_window_days` sonra → 0.0."""
        if not date_value:
            return 0.0
        if isinstance(date_value, str):
            try:
                date_value = datetime.fromisoformat(date_value)
            except ValueError:
                return 0.0
        if date_value.tzinfo is None:
            date_value = date_value.replace(tzinfo=timezone.utc)

        window = settings.search_recency_window_days
        if window <= 0:
            return 0.0
        age_days = (datetime.now(timezone.utc) - date_value).total_seconds() / 86400
        return max(0.0, 1.0 - age_days / window)

    @staticmethod
    def _stem_tr(word: str) -> str:
        """Türkçe ad çekim ekini kırpar ("beşiktaşın" → "beşiktaş").

        Gerçek morfolojik analiz değil, pragmatik bir suffix-stripping —
        en uzun ek önce denenir, kök en az 3 karakter kalmalıdır.
        """
        for suffix in _TR_SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[:-len(suffix)]
        return word

    @staticmethod
    def _tokenize(query: str) -> List[str]:
        """Sorguyu kelimelere böler ve her kelimenin TR kökünü de havuza ekler.

        SADECE SQL aday havuzunu genişletmek içindir (`keyword_search(terms=...)`)
        — hem çekimli hem kök haliyle OR koşulu kurmak zarar vermez, aday
        kümesini büyütür. Coverage/relevans skoru için BUNU KULLANMA, bkz.
        `_canonical_terms` (18 Ağu 2026'da bulunan skor seyreltme bug'ı).
        """
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
    def _canonical_terms(query: str) -> List[str]:
        """Coverage/relevans skoru için TEK terim/kelime — `_tokenize`'ın aksine

        kelimeyi VE kökünü ayrı ayrı tutmaz, sadece kökü (varsa) kullanır.
        Neden: `_stem_tr` bir SUFFIX kırpması olduğu için kök her zaman orijinal
        kelimenin bir ÖN EKİdir — kökle eşleşen her metin, orijinal kelimeyle de
        potansiyel eşleşir (substring ilişkisi). İkisini de ayrı terim sayıp
        `_keyword_relevance`'daki coverage bölenine (n) eklemek hiçbir ek bilgi
        katmadan böleni şişiriyordu: "beşiktaşın" gibi tek kelimelik ekli bir
        sorgu 2 terime (["beşiktaşın","beşiktaş"]) genişliyor, metinde SADECE
        kök eşleştiği için kapsama %50'de kalıp skor yapay olarak yarıya
        düşüyordu (0.9 yerine ~0.45) — bu da embedding aramasının ürettiği
        alakasız ama görece yüksek skorlu (~0.5) sonuçların altına düşmesine,
        yani aramanın komple alakasız sonuçlarla dolmasına yol açıyordu
        (18 Ağu 2026'da canlıda `"beşiktaşın"` ile bulundu — bkz. CLAUDE.md).
        """
        tokens = [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 2]
        return [NewsService._stem_tr(t) for t in tokens]

    @staticmethod
    def _coverage_score(title: str, summary: str, content: str, terms: List[str]) -> float:
        """Verilen terim listesinin başlık/özet/içerikte kapsama oranı — en
        iyi alan skoru döner (_FIELD_WEIGHTS). `_keyword_relevance` hem
        birincil hem ikincil (genişletme) terimler için bunu paylaşır (DRY)."""
        if not terms:
            return 0.0
        patterns = [re.compile(r"\b" + re.escape(t)) for t in terms]
        n = len(terms)
        title_hits = sum(1 for p in patterns if p.search(title))
        summary_hits = sum(1 for p in patterns if p.search(summary))
        content_hits = sum(1 for p in patterns if p.search(content))
        title_score = (title_hits / n) * _FIELD_WEIGHTS["title"]
        summary_score = (summary_hits / n) * _FIELD_WEIGHTS["summary"]
        content_score = (content_hits / n) * _FIELD_WEIGHTS["content"]
        return max(title_score, summary_score, content_score)

    @staticmethod
    def _keyword_relevance(
        article: Article,
        query_terms: List[str],
        secondary_terms: Optional[List[str]] = None,
    ) -> float:
        """Coverage tabanlı keyword skoru: terimlerin yüzde kaçı hangi alanda geçiyor.

        Alanlar ayrı puanlanır ve en iyisi alınır — başlıkta tam eşleşme,
        içerikte kısmi eşleşmeden her zaman üstündür (_FIELD_WEIGHTS).

        `query_terms` burada `_canonical_terms()`'ın çıktısı olmalı (bir orijinal
        kelime = bir terim) — `_tokenize()`'ın çıktısını (kelime+kök ayrı ayrı)
        VERME, coverage bölenini yapay şişirir (bkz. `_canonical_terms` docstring).

        Eşleşme kelimenin BAŞINDA aranır (`\\bterim`), metnin herhangi bir yerinde
        geçen ham bir alt dizi olarak DEĞİL — kök bir SUFFIX kırpması olduğu için
        orijinal kelimenin çekimli hallerini yakalamak ister ("adana" → kök "ada",
        metinde "adanada" gibi bir çekimi yakalasın), ama ham `t in text` bunu
        kelime sınırı gözetmeden yapıyordu: "ada" kökü "havadan" kelimesinin
        ORTASINDA da eşleşiyor, alakasız haberleri en üst sıraya taşıyordu
        (20 Ağu 2026'da canlıda "Adana" aramasıyla bulundu).

        `secondary_terms` (opsiyonel) — LLM sorgu genişletmesinden gelen
        ilişkili terimler ("İstanbul" → "Beykoz"). Bunlar AYRI bir coverage
        hesabıyla skorlanır ve `_EXPANSION_WEIGHT` (0.4) ile küçültülerek asıl
        skora eklenir — orijinal terimle eşleşen bir haber HER ZAMAN sadece
        genişletilmiş terimle eşleşenden üstte kalır, ama ikincisi de artık
        sıfır değildir (20 Ağu 2026, bkz. spec "arama ilişkisel genişletme").
        """
        title = article.title.lower() if article.title else ""
        summary = article.summary.lower() if article.summary else ""
        content = article.content.lower() if article.content else ""

        base = NewsService._coverage_score(title, summary, content, query_terms)
        secondary = NewsService._coverage_score(title, summary, content, secondary_terms or [])

        total = base + secondary * _EXPANSION_WEIGHT
        return round(min(total, 1.0), 4)

    def get_trending(self, hours: int = 6, limit: int = 10) -> dict:
        """Son N saatte en sık geçen entity'leri sayar (gündem listesi).

        Her entity için tip (person/organization/location) ve en fazla 3
        örnek başlık toplanır — frontend pill'lerinde tooltip olarak kullanılır.
        """
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

    @staticmethod
    def _entity_name_map(entities: Optional[dict]) -> dict:
        """{lowercased_name: original_name} — eşleştirme için küçük harf, gösterim için orijinal."""
        mapping: dict = {}
        if not isinstance(entities, dict):
            return mapping
        for values in entities.values():
            if not isinstance(values, list):
                continue
            for name in values:
                if isinstance(name, str) and len(name.strip()) >= 2:
                    clean = name.strip()
                    mapping[clean.lower()] = clean
        return mapping

    @staticmethod
    def _entity_name_set(entities: Optional[dict]) -> set:
        return set(NewsService._entity_name_map(entities).keys())

    def _find_corroborating_articles(self, article: Article, hours: int = 48) -> list:
        """`_count_corroboration` ile TAM AYNI kriteri (>=2 ortak entity, farklı
        kaynak, son `hours` saat) uygular ama sadece sayı değil gerçek (Article, skor)
        çiftlerini döner — skor = paylaşılan entity oranı (0,1].

        Bu ikisinin ortak bir yardımcıda birleşmesinin nedeni: `get_story_cluster`
        eskiden tamamen farklı bir sinyal (ChromaDB semantik embedding, eşik 0.72)
        kullanıyordu — rozet "2 kaynak doğruluyor" derken panel "kaynak bulunamadı"
        gösterebiliyordu, çünkü ikisi asla aynı şeyi ölçmüyordu (20 Ağu 2026'da
        canlıda bulundu). Artık `get_story_cluster` bu listeyi semantik sonuçlarla
        BİRLEŞTİRİYOR — rozetin saydığı kaynaklar panelde HER ZAMAN görünür.
        """
        target_map = self._entity_name_map(article.entities)
        target_keys = set(target_map)
        if len(target_keys) < 2:
            return []
        seen_sources: set = set()
        results = []
        for cand in self.repository.get_recent_articles_with_entities(hours):
            if cand.source == article.source or cand.id == article.id:
                continue
            if cand.source in seen_sources:
                continue
            shared = target_keys & self._entity_name_set(cand.entities)
            if len(shared) >= 2:
                seen_sources.add(cand.source)
                results.append((cand, round(len(shared) / len(target_keys), 4)))
        return results

    def _count_corroboration(self, article: Article) -> int:
        """Aynı olayı (>=2 ortak entity) raporlayan kaç FARKLI başka kaynak var."""
        return len(self._find_corroborating_articles(article))

    def _enrich_metadata(self, article: Article) -> None:
        """Ingest anında hesaplanan skorları işler: kalite + güvenilirlik.

        Saf hesaplama domain/scoring'dedir; bu metod sadece veri toplar ve yazar.
        """
        article.quality_score = compute_quality_score(article)
        corroboration = self._count_corroboration(article)
        article.corroboration_count = corroboration
        article.credibility_score = compute_credibility(base_credibility(article.source), corroboration)

    def get_related(self, article_id: int, limit: int = 5) -> dict:
        """Entity kesişimine göre ilgili haberleri bulur (ilişki grafı).

        Ayrı bir ilişki tablosu YOKTUR — son 500 entity'li haber on-the-fly
        taranır, ortak entity sayısına (eşitlikte tarihe) göre sıralanır.
        """
        target = self.repository.get_article_by_id(article_id)
        if target is None:
            return {"article_id": article_id, "related": []}

        target_map = self._entity_name_map(target.entities)
        target_keys = set(target_map)
        if not target_keys:
            return {"article_id": article_id, "related": []}

        scored = []
        for cand in self.repository.get_articles_with_entities(limit=500, exclude_id=article_id):
            shared_keys = target_keys & self._entity_name_set(cand.entities)
            if not shared_keys:
                continue
            shared_names = [target_map[k] for k in sorted(shared_keys)]
            scored.append((len(shared_keys), cand, shared_names))

        scored.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)

        related = [
            {
                "id": cand.id,
                "title": cand.title,
                "source": cand.source,
                "url": cand.url,
                "topic": cand.topic,
                "shared_entities": shared_names,
                "overlap": overlap,
            }
            for overlap, cand, shared_names in scored[:limit]
        ]
        return {"article_id": article_id, "related": related}

    def get_story_cluster(self, article_id: int, limit: int = 6) -> dict:
        """"Bu haberi kim nasıl anlatıyor" — aynı olayı kapsayan diğer kaynaklar
        (v2.2, rakip taraması — Ground News Blindspot'un küçük ölçekli hali).

        İki sinyali BİRLEŞTİRİR:
          1. Semantik (ChromaSearchRepository.find_similar) — farklı kelimelerle
             anlatılan ama embedding'i yakın olan makaleler.
          2. Entity-overlap (`_find_corroborating_articles`) — kartta gösterilen
             "N kaynak doğruluyor" rozetiyle (`corroboration_count`) BİREBİR AYNI
             kriter. Eskiden panel SADECE (1)'i kullanıyordu; rozet (2)'ye göre
             hesaplandığı için rozet "2 kaynak" derken panel eşik (0.72) tutmadığında
             "kaynak bulunamadı" gösterebiliyordu (20 Ağu 2026'da canlıda bulundu).
             Artık rozetin saydığı her kaynak panelde de garanti görünür.

        `search_repository` opsiyoneldir — ChromaDB yapılandırılmamışsa sadece (2)
        çalışır, çökmez. Sonuçlar skora göre azalan sıralanır, `limit` ile kesilir.
        """
        semantic: list = []
        if self.search_repository:
            try:
                semantic = self.search_repository.find_similar(article_id, n_results=limit)
            except Exception as e:
                logger.warning("Story cluster semantik arama başarısız: %s", e)

        combined: dict = {s["id"]: s for s in semantic}

        target = self.repository.get_article_by_id(article_id)
        if target:
            for cand, score in self._find_corroborating_articles(target):
                combined.setdefault(cand.id, {
                    "id": cand.id, "title": cand.title, "source": cand.source,
                    "url": cand.url, "score": score,
                })

        sources = sorted(combined.values(), key=lambda s: s["score"], reverse=True)[:limit]
        return {"article_id": article_id, "sources": sources}

    def _send_keyword_alerts(self, article: Article) -> None:
        """'instant' frekanslı abonelere keyword eşleşmesinde anında e-posta yollar."""
        if self.subscriber_repository is None or self.email_port is None:
            return
        for sub in self.subscriber_repository.get_active_subscribers():
            if sub.frequency != "instant" or not sub.keywords:
                continue
            kw = matched_keyword(article, sub.keywords)
            if kw is not None:
                self.email_port.send_alert(sub.email, article, kw, sub.language)

    def list_news_paginated(self, limit: int, before_id: Optional[int] = None, source: Optional[str] = None, sentiment: Optional[str] = None, topic: Optional[str] = None, min_quality: Optional[float] = None) -> List[Article]:
        return self.repository.get_news_paginated(limit, before_id, source, sentiment, topic, min_quality)

    def export_articles(
        self, limit: int,
        source: Optional[str] = None,
        sentiment: Optional[str] = None,
        topic: Optional[str] = None,
        min_quality: Optional[float] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Article]:
        return self.repository.get_articles_for_export(limit, source, sentiment, topic, min_quality, date_from, date_to)

    def reanalyze_missed(self, limit: int = 5) -> int:
        """Entity'si NULL kalmış haberleri tamamlar — worker her çevrim sonunda çağırır."""
        articles = self.repository.get_unanalyzed_articles(limit)
        updated = 0
        for article in articles:
            try:
                result = self.analyzer.analyze_text(article.content)
                self._apply_analysis(article, result)
                article.quality_score = compute_quality_score(article)
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
        """Analizi eksik TÜM haberleri toplu işler (POST /news/reanalyze).

        Entity'si zaten dolu olanlar atlanır — Groq kotası boşa harcanmaz.
        """
        articles = self.repository.get_all_articles()
        updated, failed, skipped = 0, 0, 0
        for article in articles:
            if article.entities is not None:
                skipped += 1
                continue
            try:
                result = self.analyzer.analyze_text(article.content)
                self._apply_analysis(article, result)
                article.quality_score = compute_quality_score(article)

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
        """Tüm haberleri ChromaDB'ye yeniden indexler (volume sıfırlandığında)."""
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