import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from src.application.services.news_service import NewsService
from src.domain.models.article import Article

def make_article(url="https://bbc.com/test"):
    return Article(title="Test", source="BBC", url=url, content="Good news today")

# recency penceresinin (search_recency_window_days) dışında — decay tabana iner:
_OLD_DATE = datetime.now(timezone.utc) - timedelta(days=100)

def make_service():
    mock_repo = MagicMock()
    mock_repo.bulk_exists.return_value = set()
    mock_repo.get_articles_by_ids.return_value = []
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_text.return_value = {
        "sentiment_score": 0.8,
        "sentiment_label": "Positive",
        "summary": "Good news today",
        "entities": {"persons": [], "organizations": [], "locations": []},
        "topic": "Other",
    }
    return NewsService(repository=mock_repo, analyzer=mock_analyzer), mock_repo, mock_analyzer

def test_update_saves_analyzed_article():
    """Haber analiz edilip kaydediliyor mu?"""
    service, mock_repo, mock_analyzer = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news = AsyncMock(return_value=[make_article()])
    mock_repo.save_article.return_value = True

    asyncio.run(service.update_news_from_source(mock_scraper))

    mock_analyzer.analyze_text.assert_called_once_with("Good news today")
    mock_repo.save_article.assert_called_once()
    saved = mock_repo.save_article.call_args[0][0]
    assert saved.sentiment_label == "Positive"
    assert saved.sentiment_score == 0.8
    assert saved.summary == "Good news today"

def test_update_multiple_articles():
    """Birden fazla haber kaydediliyor mu?"""
    service, mock_repo, _ = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news = AsyncMock(return_value=[
        make_article("https://bbc.com/1"),
        make_article("https://bbc.com/2"),
        make_article("https://bbc.com/3"),
    ])
    mock_repo.save_article.return_value = True

    # Haber başına 2sn'lik Groq throttle'ı bu testi 4 saniye bekletiyordu;
    # test throttle'ı değil kaydetme sayısını doğruluyor.
    with patch("src.application.services.news_service.asyncio.sleep", new=AsyncMock()):
        asyncio.run(service.update_news_from_source(mock_scraper))

    assert mock_repo.save_article.call_count == 3

def test_update_respects_max_new_articles_cap():
    """max_new_articles verilirse bu çalıştırmada sadece o kadarı analiz edilir —
    kalanlar kaydedilmediği için (bulk_exists hâlâ 'yeni' görecek) sonraki taramaya
    kalır. Bir kaynağın devasa yeni-haber kuyruğu, worker'ı diğer 16 kaynaktan
    saatlerce alıkoymasın diye (bkz. CLAUDE.md 'startup scrape' notu)."""
    service, mock_repo, mock_analyzer = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news = AsyncMock(return_value=[
        make_article("https://bbc.com/1"),
        make_article("https://bbc.com/2"),
        make_article("https://bbc.com/3"),
    ])
    mock_repo.save_article.return_value = True

    with patch("src.application.services.news_service.asyncio.sleep", new=AsyncMock()):
        asyncio.run(service.update_news_from_source(mock_scraper, max_new_articles=2))

    assert mock_repo.save_article.call_count == 2
    assert mock_analyzer.analyze_text.call_count == 2

def test_update_throttle_uses_configured_interval():
    """Makaleler arası bekleme artık sabit 2sn değil, settings.groq_request_
    interval_seconds'tan okunuyor — eski sabit RPM=30'u hedefliyordu ama
    Groq'un asıl darboğazı TPM=8000 idi, 2sn bunun için fazla hızlıydı
    (1 Eyl 2026, canlı teşhis, bkz. CLAUDE.md roadmap #25)."""
    from src.infrastructure.config.settings import settings
    service, mock_repo, _ = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news = AsyncMock(return_value=[
        make_article("https://bbc.com/1"),
        make_article("https://bbc.com/2"),
    ])
    mock_repo.save_article.return_value = True

    with patch("src.application.services.news_service.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        asyncio.run(service.update_news_from_source(mock_scraper))

    mock_sleep.assert_called_once_with(settings.groq_request_interval_seconds)

def test_reanalyze_missed_throttles_between_calls():
    """reanalyze_missed art arda (0sn boşlukla) Groq çağrısı yapıyordu — TPM
    kovasını (leaky bucket) anlık patlatan 3 burst kaynağından biriydi (bkz.
    roadmap #25, 1 Eyl 2026 canlı teşhis). Artık update_news_from_source ile
    AYNI güvenli aralığı paylaşmalı."""
    from src.infrastructure.config.settings import settings
    service, mock_repo, mock_analyzer = make_service()
    articles = [make_article(f"https://bbc.com/{i}") for i in range(3)]
    mock_repo.get_unanalyzed_articles.return_value = articles
    mock_repo.update_article_analysis.return_value = True

    with patch("src.application.services.news_service.time.sleep") as mock_sleep:
        service.reanalyze_missed(3)

    # 3 makale = ilk çağrıdan önce bekleme yok, aralarda 2 bekleme
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(settings.groq_request_interval_seconds)

def test_reanalyze_missed_single_article_does_not_throttle():
    """Tek makale varsa beklenecek ikinci bir çağrı yok, sleep hiç çağrılmaz."""
    service, mock_repo, mock_analyzer = make_service()
    mock_repo.get_unanalyzed_articles.return_value = [make_article()]
    mock_repo.update_article_analysis.return_value = True

    with patch("src.application.services.news_service.time.sleep") as mock_sleep:
        service.reanalyze_missed(1)

    mock_sleep.assert_not_called()

def test_update_empty_source():
    """Scraper boş liste dönerse hata vermemeli"""
    service, mock_repo, mock_analyzer = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news = AsyncMock(return_value=[])

    asyncio.run(service.update_news_from_source(mock_scraper))

    mock_analyzer.analyze_text.assert_not_called()
    mock_repo.save_article.assert_not_called()

def test_update_skips_existing_articles():
    """bulk_exists ile zaten var olan haberler analiz edilmez."""
    service, mock_repo, mock_analyzer = make_service()
    mock_repo.bulk_exists.return_value = {"https://bbc.com/test"}
    mock_scraper = MagicMock()
    mock_scraper.fetch_news = AsyncMock(return_value=[make_article()])

    asyncio.run(service.update_news_from_source(mock_scraper))

    mock_analyzer.analyze_text.assert_not_called()
    mock_repo.save_article.assert_not_called()

def test_list_news_passes_filters():
    """list_news filteleri repository'ye iletiyor mu?"""
    service, mock_repo, _ = make_service()
    mock_repo.get_latest_news.return_value = []

    service.list_news(limit=5, sentiment="Positive")

    mock_repo.get_latest_news.assert_called_once_with(5, "Positive")


# ── hybrid_search ─────────────────────────────────────────────────────────────

def make_service_with_search():
    service, mock_repo, mock_analyzer = make_service()
    mock_search = MagicMock()
    service.search_repository = mock_search
    return service, mock_repo, mock_search


# ── _distinguishing_query_terms / _grounding_factor (sorgu-varlık doğrulaması) ─

def test_distinguishing_query_terms_extracts_capitalized_first_word():
    # Dünkü canlı bug'ın TAM senaryosu: sorgu konu-önce yazılıyor, özel isim
    # genelde İLK kelime — cümle-başı hariç tutulsaydı bu senaryo kaçırılırdı.
    assert NewsService._distinguishing_query_terms("Beşiktaş maçı saat kaçta") == ["Beşiktaş"]


def test_distinguishing_query_terms_single_word_query_still_checked():
    assert NewsService._distinguishing_query_terms("Beşiktaş") == ["Beşiktaş"]


def test_distinguishing_query_terms_strips_trailing_punctuation():
    assert NewsService._distinguishing_query_terms("bu akşam Beşiktaş? maçı var mı") == ["Beşiktaş"]


def test_distinguishing_query_terms_empty_for_all_lowercase_query():
    assert NewsService._distinguishing_query_terms("maç saat kaçta") == []


def test_distinguishing_query_terms_multiple_capitalized_words():
    assert NewsService._distinguishing_query_terms("Beşiktaş Zalgiris maçı") == ["Beşiktaş", "Zalgiris"]


def test_grounding_factor_neutral_when_no_distinguishing_terms():
    article = Article(title="Herhangi bir haber", source="BBC", url="u", content="içerik")
    assert NewsService._grounding_factor([], article) == 1.0


def test_grounding_factor_full_when_term_present_in_title():
    article = Article(title="Beşiktaş kazandı", source="BBC", url="u", content="içerik")
    assert NewsService._grounding_factor(["Beşiktaş"], article) == 1.0


def test_grounding_factor_full_when_term_present_only_in_content():
    article = Article(title="Maç sonucu", source="BBC", url="u", content="Beşiktaş sahadan galip ayrıldı")
    assert NewsService._grounding_factor(["Beşiktaş"], article) == 1.0


def test_grounding_factor_penalized_when_term_absent():
    article = Article(title="Filenin Sultanları kazandı", source="BBC", url="u", content="voleybol maçı")
    assert NewsService._grounding_factor(["Beşiktaş"], article) == 0.3


def test_grounding_factor_case_insensitive_dotted_i_safe():
    # dotted-İ dersi: sorgudaki "İstanbul" makaledeki "istanbul" ile eşleşmeli
    article = Article(title="istanbulda etkinlik", source="BBC", url="u", content="içerik")
    assert NewsService._grounding_factor(["İstanbul"], article) == 1.0


def test_hybrid_search_without_expander_matches_old_behavior():
    """query_expander verilmezse davranış eskisiyle BİREBİR aynı kalmalı."""
    service, mock_repo, _ = make_service()
    service.search_repository = None
    keyword_article = make_article()
    keyword_article.id = 1
    # Not using Turkish "İstanbul'da toplantı" from brief: Python's str.lower() on
    # capital dotted İ (U+0130) produces a 2-codepoint sequence that breaks
    # _coverage_score's \b-anchored regex. This is a pre-existing bug (out of scope).
    keyword_article.title = "Istanbul meeting today"
    mock_repo.keyword_search.return_value = [keyword_article]

    results = service.hybrid_search("istanbul")

    assert len(results) == 1
    mock_repo.keyword_search.assert_called_once()
    called_terms = mock_repo.keyword_search.call_args.kwargs["terms"]
    assert "istanbul" in called_terms


def test_hybrid_search_includes_secondary_match_via_expander():
    """query_expander "beykoz" döndürürse, sadece "Beykoz" geçen (İstanbul
    geçmeyen) bir haber de artık sonuçlarda görünmeli — düşük skorla."""
    mock_repo = MagicMock()
    mock_search = MagicMock()
    mock_expander = MagicMock()
    mock_expander.expand.return_value = ["beykoz"]
    mock_search.search.return_value = []

    beykoz_article = make_article()
    beykoz_article.id = 7
    beykoz_article.title = "Beykoz'da yeni bir proje açıldı"
    beykoz_article.summary = None
    mock_repo.keyword_search.return_value = [beykoz_article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=mock_search, query_expander=mock_expander,
    )

    results = service.hybrid_search("istanbul")

    assert len(results) == 1
    assert results[0]["id"] == "7"
    assert 0.0 < results[0]["score"] < 0.9
    mock_expander.expand.assert_called_once_with("istanbul")
    called_terms = mock_repo.keyword_search.call_args.kwargs["terms"]
    assert "beykoz" in called_terms


def test_hybrid_search_expander_failure_falls_back_to_original_query():
    """expand() exception fırlatırsa arama SESSİZCE orijinal sorguyla devam
    etmeli, hybrid_search hiç patlamamalı."""
    mock_repo = MagicMock()
    mock_expander = MagicMock()
    mock_expander.expand.side_effect = RuntimeError("Groq çöktü")

    keyword_article = make_article()
    keyword_article.id = 3
    keyword_article.title = "yapay zeka haberi"
    keyword_article.summary = None
    mock_repo.keyword_search.return_value = [keyword_article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    results = service.hybrid_search("yapay zeka")

    assert len(results) == 1
    assert results[0]["id"] == "3"


def test_hybrid_search_expander_case_insensitivity_titlecase_expansion():
    """GroqQueryExpander Title-Case çıktı döner ("Beykoz" gibi). Bunları
    lowercase'lemeden secondary_terms'e geçmek matching başarısız kılardı.
    Düzeltme: expanded_terms bir kez lowercase'le, hem SQL hem secondary için kullan."""
    mock_repo = MagicMock()
    mock_search = MagicMock()
    mock_expander = MagicMock()
    # Gerçek LLM çıktısı gibi Title-Case:
    mock_expander.expand.return_value = ["Beykoz", "Fatih"]
    mock_search.search.return_value = []

    article = make_article()
    article.id = 42
    article.title = "Beykoz'da büyük proje başladı"
    article.summary = None
    mock_repo.keyword_search.return_value = [article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=mock_search, query_expander=mock_expander,
    )

    results = service.hybrid_search("istanbul")

    assert len(results) == 1
    assert results[0]["id"] == "42"
    assert 0.0 < results[0]["score"] < 0.9  # secondary terms ağırlığı ile düşük
    # Verify lowercased terms were used in SQL:
    called_terms = mock_repo.keyword_search.call_args.kwargs["terms"]
    assert "beykoz" in called_terms
    assert "fatih" in called_terms


def test_hybrid_search_expander_malformed_result_not_fail_open():
    """expand() None döndürse (ya da başka non-list), list comprehension TypeError
    fırlatacaktır. Fail-open prensibi: isinstance check ile boş liste default'ı."""
    mock_repo = MagicMock()
    mock_expander = MagicMock()
    mock_expander.expand.return_value = None  # Malformed result

    article = make_article()
    article.id = 10
    article.title = "test article"
    article.summary = None
    mock_repo.keyword_search.return_value = [article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    # Should not raise TypeError, should fallback gracefully
    results = service.hybrid_search("test")

    assert len(results) == 1
    assert results[0]["id"] == "10"


def test_hybrid_search_expander_malformed_element_does_not_crash():
    """Liste KONTEYNIRI doğru ama ELEMANLARI değilse (eski/yabancı bir `qexp:`
    Redis anahtarı böyle bir şey taşıyabilir) `.lower()` AttributeError fırlatır
    ve hybrid_search'ten kaçardı. Sadece geçerli string'ler kullanılmalı."""
    mock_repo = MagicMock()
    mock_expander = MagicMock()
    mock_expander.expand.return_value = ["beykoz", 42, None, "  ", "fatih"]

    article = make_article()
    article.id = 11
    article.title = "Beykoz'da yeni proje"
    article.summary = None
    mock_repo.keyword_search.return_value = [article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    results = service.hybrid_search("istanbul")

    assert len(results) == 1
    assert results[0]["id"] == "11"
    # Sadece geçerli string'ler SQL'e gitmeli; 42/None/"  " elenmiş olmalı.
    secondary_terms = mock_repo.keyword_search.call_args.kwargs["terms"]
    assert secondary_terms == ["beykoz", "fatih"]


def test_hybrid_search_secondary_terms_use_separate_query_with_own_budget():
    """Birincil ve ikincil terimler TEK bir OR'lu sorgunun LIMIT'ini
    paylaşmamalı: yaygın bir ikincil terim ("fatih" aynı zamanda sık bir isim)
    havuzu doldurup gerçek birincil eşleşmeleri dışarıda bırakabiliyordu.
    İki AYRI sorgu → her iki taraf da sonuçlarda görünür."""
    primary_article = make_article("https://bbc.com/p")
    primary_article.id = 1
    primary_article.title = "istanbul'da toplantı yapıldı"
    primary_article.summary = None

    secondary_article = make_article("https://bbc.com/s")
    secondary_article.id = 2
    secondary_article.title = "fatih'te yeni proje açıldı"
    secondary_article.summary = None

    def keyword_search_side_effect(query, limit, source, sentiment, terms=None):
        # Birincil sorgu SADECE birincil eşleşmeyi, ikincil sorgu SADECE
        # ikincil eşleşmeyi döndürür (gerçek SQL'de olduğu gibi ayrık).
        if "fatih" in (terms or []):
            return [secondary_article]
        return [primary_article]

    mock_repo = MagicMock()
    mock_repo.keyword_search.side_effect = keyword_search_side_effect
    mock_expander = MagicMock()
    mock_expander.expand.return_value = ["fatih"]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    results = service.hybrid_search("istanbul")

    assert mock_repo.keyword_search.call_count == 2
    ids = {r["id"] for r in results}
    assert ids == {"1", "2"}

    # İkincil sorgu birincilden DAHA KÜÇÜK bir bütçe kullanmalı (havuzu çalmaz).
    primary_call, secondary_call = mock_repo.keyword_search.call_args_list
    assert primary_call.kwargs["terms"] == service._tokenize("istanbul")
    assert secondary_call.kwargs["terms"] == ["fatih"]
    assert secondary_call.args[1] < primary_call.args[1]


def test_hybrid_search_one_failing_query_does_not_kill_the_other():
    """İki keyword sorgusu BAĞIMSIZ fail-open: birincil patlasa bile ikincil
    sonuçları (ve tersi) yine de kullanılmalı."""
    secondary_article = make_article("https://bbc.com/s")
    secondary_article.id = 5
    secondary_article.title = "beykoz'da yeni proje"
    secondary_article.summary = None

    def keyword_search_side_effect(query, limit, source, sentiment, terms=None):
        if "beykoz" in (terms or []):
            return [secondary_article]
        raise RuntimeError("birincil SQL çöktü")

    mock_repo = MagicMock()
    mock_repo.keyword_search.side_effect = keyword_search_side_effect
    mock_expander = MagicMock()
    mock_expander.expand.return_value = ["beykoz"]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    results = service.hybrid_search("istanbul")

    assert [r["id"] for r in results] == ["5"]


def test_hybrid_search_no_second_query_when_nothing_to_expand():
    """Genişletme yoksa (boş liste) ikincil sorgu HİÇ atılmamalı — boşuna
    bir DB turu olurdu."""
    mock_repo = MagicMock()
    mock_expander = MagicMock()
    mock_expander.expand.return_value = []

    article = make_article()
    article.id = 9
    article.title = "istanbul'da toplantı"
    article.summary = None
    mock_repo.keyword_search.return_value = [article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    service.hybrid_search("istanbul")

    mock_repo.keyword_search.assert_called_once()


def test_hybrid_search_dedups_article_present_in_both_queries():
    """İki sorgu da aynı makaleyi döndürürse sonuçta bir kez görünmeli."""
    article = make_article()
    article.id = 3
    article.title = "istanbul beykoz haberi"
    article.summary = None

    mock_repo = MagicMock()
    mock_repo.keyword_search.return_value = [article]
    mock_expander = MagicMock()
    mock_expander.expand.return_value = ["beykoz"]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    results = service.hybrid_search("istanbul")

    assert len(results) == 1
    assert results[0]["id"] == "3"


def test_hybrid_search_returns_semantic_results():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Semantic Haber", "summary": "s", "source": "BBC", "url": "u", "score": 0.9,
         "published_at": datetime.now(timezone.utc).isoformat()}
    ]
    mock_repo.keyword_search.return_value = []

    results = service.hybrid_search("yapay zeka", n_results=5)

    assert len(results) == 1
    # credibility_score=None (fetch edilmedi) -> credibility_factor=0.85: 0.9*0.85
    assert results[0]["score"] == 0.765
    # candidate_size = max(5*3, 20) = 20
    mock_search.search.assert_called_once_with("yapay zeka", 20, None, None)


def test_hybrid_search_merges_keyword_only_results():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Semantic", "summary": "", "source": "BBC", "url": "u1", "score": 0.5}
    ]
    keyword_article = make_article("https://bbc.com/keyword")
    keyword_article.id = 2
    keyword_article.title = "Keyword haberi özeli"
    keyword_article.summary = "keyword özeti"
    mock_repo.keyword_search.return_value = [keyword_article]

    results = service.hybrid_search("keyword")

    result_ids = {r["id"] for r in results}
    assert len(results) == 2
    assert "1" in result_ids
    assert "2" in result_ids
    # "keyword" başlıkta geçiyor → skor 0.90 > semantic 0.50 → keyword result önde
    assert results[0]["id"] == "2"
    # credibility_score=None -> credibility_factor=0.85: 0.90*0.85
    assert results[0]["score"] == 0.765


def test_hybrid_search_deduplicates_overlapping_results():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Ortak Haber", "summary": "", "source": "BBC", "url": "u", "score": 0.7}
    ]
    overlap_article = make_article()
    overlap_article.id = 1
    mock_repo.keyword_search.return_value = [overlap_article]

    results = service.hybrid_search("test")

    assert len(results) == 1


def test_hybrid_search_falls_back_to_keyword_when_no_search_repo():
    service, mock_repo, _ = make_service()
    service.search_repository = None
    keyword_article = make_article()
    keyword_article.id = 5
    keyword_article.title = "Fallback haberi burada"
    mock_repo.keyword_search.return_value = [keyword_article]

    results = service.hybrid_search("fallback")

    assert len(results) == 1
    assert results[0]["id"] == "5"
    # "fallback" başlıkta → 0.90, credibility_score=None -> credibility_factor=0.85
    assert results[0]["score"] == 0.765


def test_hybrid_search_boosts_result_found_in_both():
    """Hem semantic hem keyword'de bulunan article double-hit bonus alır."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Real Madrid haberi", "summary": "", "source": "BBC", "url": "u", "score": 0.6}
    ]
    boosted_article = make_article()
    boosted_article.id = 1
    boosted_article.title = "Real Madrid yıldız transferi"  # 2/2 query kelimesi başlıkta
    mock_repo.keyword_search.return_value = [boosted_article]

    results = service.hybrid_search("real madrid")

    assert results[0]["id"] == "1"
    # max(sem=0.6, kw=0.9) + bonus=0.10 = 1.0 (cap), credibility_score=None -> 0.85
    assert results[0]["score"] == 0.85


def test_hybrid_search_keyword_only_ranks_above_low_semantic():
    """Başlık eşleşmesi (0.90) düşük semantik skorun önüne geçmeli."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "99", "title": "Alakasız haber", "summary": "", "source": "X", "url": "u", "score": 0.3}
    ]
    exact_article = make_article("https://bbc.com/real-madrid")
    exact_article.id = 7
    exact_article.title = "Real Madrid yıldızla yollarını ayırdı"
    mock_repo.keyword_search.return_value = [exact_article]

    results = service.hybrid_search("real madrid", n_results=2)

    assert results[0]["id"] == "7"   # başlık eşleşmesi (0.90) önde
    # credibility_score=None -> credibility_factor=0.85: 0.90*0.85
    assert results[0]["score"] == 0.765
    assert results[1]["id"] == "99"  # düşük semantic (0.30) arkada


def test_hybrid_search_recency_bonus_ranks_fresh_article_above_old_equal_score():
    """Aynı keyword skoruna sahip iki sonuçtan yeni tarihli olan üstte çıkmalı."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = []

    fresh = make_article("https://bbc.com/fresh")
    fresh.id = 1
    fresh.title = "Hava durumu bugün"  # 2/2 başlıkta → 0.9
    fresh.created_at = datetime.now(timezone.utc)

    stale = make_article("https://bbc.com/stale")
    stale.id = 2
    stale.title = "Hava durumu geçen ay"  # 2/2 başlıkta → 0.9 (aynı base skor)
    stale.created_at = _OLD_DATE

    mock_repo.keyword_search.return_value = [stale, fresh]  # sıra önemli değil

    results = service.hybrid_search("hava durumu", n_results=5)

    assert results[0]["id"] == "1"  # taze haber recency bonus ile önde
    assert results[0]["score"] > results[1]["score"]
    assert results[1]["id"] == "2"


def test_recency_factor_zero_for_missing_date():
    assert NewsService._recency_factor(None) == 0.0
    assert NewsService._recency_factor("") == 0.0


def test_recency_factor_full_for_today():
    assert NewsService._recency_factor(datetime.now(timezone.utc)) > 0.999


def test_recency_factor_zero_beyond_window():
    assert NewsService._recency_factor(_OLD_DATE) == 0.0


def test_recency_factor_accepts_iso_string():
    iso = datetime.now(timezone.utc).isoformat()
    assert NewsService._recency_factor(iso) > 0.999


# ── hybrid_search grounding/credibility/trust_score entegrasyonu ──────────────

def test_hybrid_search_penalizes_semantic_result_missing_query_entity():
    """Dünkü 'maç' bug'ı: yüksek semantik skorlu ama sorgudaki özel ismi
    (Beşiktaş) içermeyen bir sonuç, düşük semantik skorlu ama özel ismi
    içeren bir sonucun ALTINA düşmeli."""
    service, mock_repo, mock_search = make_service_with_search()

    off_topic = make_article("https://x.com/1")
    off_topic.id = 1
    off_topic.title = "Filenin Sultanları kazandı"
    off_topic.content = "voleybol maçı heyecanı"

    on_topic = make_article("https://x.com/2")
    on_topic.id = 2
    on_topic.title = "Beşiktaş kazandı"
    on_topic.content = "futbol maçı sonucu"

    mock_search.search.return_value = [
        {"id": "1", "title": off_topic.title, "summary": "", "source": "BBC", "url": off_topic.url, "score": 0.85, "published_at": None},
        {"id": "2", "title": on_topic.title, "summary": "", "source": "BBC", "url": on_topic.url, "score": 0.50, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [off_topic, on_topic]

    results = service.hybrid_search("Beşiktaş maçı saat kaçta", n_results=5)

    scores = {r["id"]: r["score"] for r in results}
    assert scores["2"] > scores["1"]


def test_hybrid_search_no_distinguishing_term_leaves_ranking_unchanged():
    """Sorguda özel isim yoksa (ör. 'futbol haberleri') grounding hiç devreye
    girmemeli — mevcut sıralama davranışı bozulmamalı. credibility_score=None
    olduğu için 0.7+0.3*0.5=0.85 credibility_factor'ü yine de uygulanır
    (grounding'den BAĞIMSIZ bir çarpan), bu yüzden 0.7 değil 0.595 beklenir.
    published_at bilinçli olarak "şimdi" veriliyor — recency decay'i 1.0'a
    sabitleyip bu testi SADECE grounding+credibility'yi izole etmesi için
    (decay ayrı testlerde zaten kapsanıyor, bkz. _decay_factor bloğu)."""
    service, mock_repo, mock_search = make_service_with_search()
    art = make_article("https://x.com/1")
    art.id = 1
    mock_search.search.return_value = [
        {"id": "1", "title": art.title, "summary": "", "source": "BBC", "url": art.url, "score": 0.7,
         "published_at": datetime.now(timezone.utc).isoformat()},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [art]

    results = service.hybrid_search("futbol haberleri", n_results=5)

    assert results[0]["score"] == 0.595


def test_hybrid_search_low_credibility_source_dampened_not_zeroed():
    service, mock_repo, mock_search = make_service_with_search()
    art = make_article("https://x.com/1")
    art.id = 1
    art.credibility_score = 0.0
    mock_search.search.return_value = [
        {"id": "1", "title": art.title, "summary": "", "source": "BBC", "url": art.url, "score": 0.8, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [art]

    results = service.hybrid_search("haberler", n_results=5)

    assert 0 < results[0]["score"] < 0.8  # geriye düştü ama sıfırlanmadı


def test_hybrid_search_results_include_trust_score():
    service, mock_repo, mock_search = make_service_with_search()
    art = make_article("https://x.com/1")
    art.id = 1
    art.quality_score = 1.0
    art.credibility_score = 1.0
    art.corroboration_count = 10
    mock_search.search.return_value = [
        {"id": "1", "title": art.title, "summary": "", "source": "BBC", "url": art.url, "score": 0.9, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [art]

    results = service.hybrid_search("haberler", n_results=5)

    assert results[0]["trust_score"] == 100


def test_hybrid_search_get_articles_by_ids_failure_is_fail_open():
    """Article fetch'i patlarsa arama çökmemeli, sadece grounding/credibility/
    trust_score nötr değerlere düşmeli."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Bir haber", "summary": "", "source": "BBC", "url": "u", "score": 0.6, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.side_effect = Exception("db down")

    results = service.hybrid_search("haberler", n_results=5)

    assert len(results) == 1
    assert results[0]["trust_score"] == 40  # None/None/0 nötr varsayılan


# ── _decay_factor ─────────────────────────────────────────────────────────────

def test_decay_factor_full_recency_is_near_one():
    assert NewsService._decay_factor(1.0) == pytest.approx(1.0)


def test_decay_factor_zero_recency_equals_floor():
    from src.infrastructure.config.settings import settings
    assert NewsService._decay_factor(0.0) == pytest.approx(settings.search_recency_decay_floor)


def test_decay_factor_midpoint_is_between_floor_and_one():
    from src.infrastructure.config.settings import settings
    floor = settings.search_recency_decay_floor
    expected = floor + (1 - floor) * 0.5
    assert NewsService._decay_factor(0.5) == pytest.approx(expected)


def test_hybrid_search_recency_decay_reorders_equal_relevance_results():
    """Tam başlık eşleşmesi + double-hit bonus relevance'ı zaten 1.0'a ulaştırınca
    (additive bonus ile bunun skorda hiç yeri kalmıyordu) çarpımsal decay devreye
    girip tarihe göre gerçek bir ayrışma yaratmalı — gerçek prod'da tespit edilen
    bug: 31 günlük haber, bugünkü haberin önüne geçiyordu."""
    service, mock_repo, mock_search = make_service_with_search()

    def _capped_article(id_, url, days_old):
        a = make_article(url)
        a.id = id_
        a.title = "Hava Durumu Tahminleri"  # 2/2 başlıkta → keyword base 0.9
        a.created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
        return a

    very_old = _capped_article(1, "https://bbc.com/very-old", 31)   # pencere dışı → decay=floor
    mid_old = _capped_article(2, "https://bbc.com/mid-old", 27)     # kısmi decay
    fresh = _capped_article(3, "https://bbc.com/fresh", 0)          # decay≈1.0

    # Her üçü hem semantik hem keyword'de bulunsun → double-hit bonus (0.10) ile
    # relevance = base(0.9)+bonus(0.10) = 1.0 zaten cap'e takılıyor (gerçek prod
    # senaryosu) — additive bonus'ta bu üçünü ayırt etmenin yolu yoktu.
    mock_search.search.return_value = [
        {"id": str(a.id), "title": a.title, "summary": "", "source": "BBC", "url": a.url, "score": 0.9}
        for a in (very_old, mid_old, fresh)
    ]
    mock_repo.keyword_search.return_value = [very_old, mid_old, fresh]

    results = service.hybrid_search("hava durumu", n_results=5)

    assert [r["id"] for r in results] == ["3", "2", "1"]  # taze → orta → eski
    scores = [r["score"] for r in results]
    assert scores[0] > scores[1] > scores[2]               # çarpımsal decay artık gerçekten ayrıştırıyor
    # very_old: relevance(1.0) * floor(0.5) * credibility_factor(0.85, credibility_score=None)
    assert scores[2] == pytest.approx(0.425, abs=0.001)


def test_hybrid_search_passes_filters_to_both():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = []
    mock_repo.keyword_search.return_value = []

    service.hybrid_search("filtreli", n_results=3, source="TRT Haber", sentiment="Positive")

    # candidate_size = max(3*3, 20) = 20
    # "filtreli" → stem strips "-li" → "filtre"; terms == ["filtreli", "filtre"]
    mock_search.search.assert_called_once_with("filtreli", 20, "TRT Haber", "Positive")
    mock_repo.keyword_search.assert_called_once_with("filtreli", 20, "TRT Haber", "Positive", terms=["filtreli", "filtre"])


# ── _tokenize / _keyword_relevance birim testleri ────────────────────────────

def test_tokenize_lowercases_and_filters_short():
    assert NewsService._tokenize("a I to ai yapay") == ["to", "ai", "yapay"]


def test_tokenize_preserves_unicode():
    assert NewsService._tokenize("Beşiktaş'a transfer") == ["beşiktaş", "transfer"]


def test_tokenize_expands_turkish_suffixes():
    tokens = NewsService._tokenize("beşiktaşın hocası")
    assert "beşiktaşın" in tokens
    assert "beşiktaş" in tokens   # genitive stripped
    assert "hocası" in tokens
    assert "hoca" in tokens        # 3rd-person possessive stripped


def test_stem_tr_common_cases():
    assert NewsService._stem_tr("beşiktaşın") == "beşiktaş"   # genitive -ın
    assert NewsService._stem_tr("hocası") == "hoca"             # possessive -sı
    assert NewsService._stem_tr("fenerbahçenin") == "fenerbahçe"  # genitive -nin
    assert NewsService._stem_tr("galatasaraydan") == "galatasaray"  # ablative -dan
    assert NewsService._stem_tr("haberlerin") == "haber"         # plural genitive -lerin
    assert NewsService._stem_tr("filtreli") == "filtre"          # adjective-forming -li
    assert NewsService._stem_tr("köylü") == "köy"                # adjective-forming -lü
    assert NewsService._stem_tr("yapay") == "yapay"              # no suffix → unchanged
    assert NewsService._stem_tr("ev") == "ev"                    # too short to strip


def test_tokenize_empty_query():
    assert NewsService._tokenize("") == []
    assert NewsService._tokenize("   ") == []


def test_keyword_relevance_full_title_match():
    article = make_article()
    article.title = "Yapay zeka çağı"
    article.summary = None
    relevance = NewsService._keyword_relevance(article, ["yapay", "zeka"])
    assert relevance == 0.9  # 2/2 × 0.9


def test_keyword_relevance_partial_title_match():
    article = make_article()
    article.title = "Sadece yapay haberi"
    article.summary = None
    article.content = "alakasız içerik"
    relevance = NewsService._keyword_relevance(article, ["yapay", "zeka"])
    assert relevance == 0.45  # 1/2 × 0.9


def test_keyword_relevance_summary_beats_partial_title():
    article = make_article()
    article.title = "yapay haberi"          # 1/2 × 0.9 = 0.45
    article.summary = "yapay zeka çok güzel"  # 2/2 × 0.7 = 0.70
    article.content = ""
    relevance = NewsService._keyword_relevance(article, ["yapay", "zeka"])
    assert relevance == 0.7  # max() seçer


def test_keyword_relevance_content_only_match():
    article = make_article()
    article.title = "alakasız başlık"
    article.summary = "alakasız özet"
    article.content = "burada yapay zeka geçiyor"
    relevance = NewsService._keyword_relevance(article, ["yapay", "zeka"])
    assert relevance == 0.5  # 2/2 × 0.5 (content weight) = 0.5


def test_keyword_relevance_empty_terms():
    article = make_article()
    assert NewsService._keyword_relevance(article, []) == 0.0


def test_keyword_relevance_secondary_terms_add_small_bonus():
    """Sadece ikincil (genişletilmiş) terim geçen makale sıfırdan farklı, ama
    birincil terimin verdiği skordan daha düşük bir skor almalı."""
    article = make_article()
    article.title = "Beykoz'da yeni bir proje açıldı"
    article.summary = None
    article.content = "alakasız içerik"
    relevance = NewsService._keyword_relevance(article, ["istanbul"], secondary_terms=["beykoz"])
    assert 0.0 < relevance < 0.9  # sadece "istanbul" geçseydi 0.9 olurdu


def test_keyword_relevance_full_primary_beats_full_secondary():
    """AYNI güçte (başlıkta tam kapsama) bir birincil eşleşme, ikincil
    eşleşmeyi geçer — çünkü ikincil katkı `_EXPANSION_WEIGHT` ile küçültülür.

    DİKKAT: bu "birincil HER ZAMAN kazanır" demek DEĞİLDİR. Garanti sadece
    tavanlar üzerinedir (ikincil ≤ 0.36 < birincil ≤ 0.9); zayıf/kısmi bir
    birincil eşleşme güçlü bir ikincil eşleşmenin altında kalabilir — bkz.
    `_keyword_relevance` docstring'i.
    """
    article_primary = make_article()
    article_primary.title = "istanbul'da toplantı yapıldı"
    article_primary.summary = None
    article_primary.content = "alakasız içerik"

    article_secondary = make_article()
    article_secondary.title = "beykoz'da toplantı yapıldı"
    article_secondary.summary = None
    article_secondary.content = "alakasız içerik"

    primary_score = NewsService._keyword_relevance(article_primary, ["istanbul"], secondary_terms=["beykoz"])
    secondary_score = NewsService._keyword_relevance(article_secondary, ["istanbul"], secondary_terms=["beykoz"])

    assert primary_score > secondary_score


def test_keyword_relevance_no_secondary_terms_matches_old_behavior():
    article = make_article()
    article.title = "Yapay zeka çağı"
    article.summary = None
    relevance = NewsService._keyword_relevance(article, ["yapay", "zeka"], secondary_terms=None)
    assert relevance == 0.9


def test_keyword_relevance_score_never_exceeds_one():
    article = make_article()
    article.title = "istanbul beykoz"
    article.summary = None
    article.content = ""
    relevance = NewsService._keyword_relevance(article, ["istanbul"], secondary_terms=["beykoz"])
    assert relevance <= 1.0


def test_keyword_relevance_no_mid_word_false_positive():
    """"adana" araması, kökü "ada" olduğu için "havadan" gibi alakasız bir
    kelimenin İÇİNDE geçen "ada" alt dizisini eşleştirmemeli (20 Ağu 2026'da
    canlıda bulundu: "Adana" araması en yüksek skorla "havadan" geçen alakasız
    bir habere gidiyordu). Kök yalnızca bir kelimenin BAŞINDA eşleşmeli
    (çekim eki bulma niyeti budur — bkz. `_canonical_terms` docstring),
    kelimenin ortasında rastgele bir alt dizi olarak değil.
    """
    article = make_article()
    article.title = "Bakanlıktan havadan görüntüler paylaşıldı"
    article.summary = None
    article.content = "alakasız içerik"
    relevance = NewsService._keyword_relevance(article, NewsService._canonical_terms("adana"))
    assert relevance == 0.0


def test_keyword_relevance_still_matches_inflected_word_start():
    """Kök eşleşmesi kelimenin BAŞINDA olduğu sürece hâlâ çalışmalı (regresyon
    olmasın diye) — "adana" sorgusu "adanada" gibi çekimli bir formu bulmalı."""
    article = make_article()
    article.title = "Adanada deprem hissedildi"
    article.summary = None
    article.content = "alakasız içerik"
    relevance = NewsService._keyword_relevance(article, NewsService._canonical_terms("adana"))
    assert relevance == 0.9  # 1/1 × 0.9 (title)


def test_keyword_relevance_dotted_capital_i_title_still_matches():
    """27 Ağu 2026'da RAG canlı QA'sında bulundu: Python'un varsayılan
    `.lower()`'ı Türkçe büyük "İ"yi (U+0130) tek bir "i" değil "i" + birleşen
    nokta işaretine çeviriyor ("İsrailli".lower() -> "i̇srailli") — bu da
    "\\bisrail" gibi bir eşleşmenin başlangıç noktasını bozup KAÇMASINA yol
    açıyordu. "İsrailli bakandan Türkiye açıklaması!" başlıklı gerçek bir
    haber "israil" sorgusuyla hiç eşleşmiyordu (RAG kanıt kapısı yanlışlıkla
    "kanıt yok" diyordu)."""
    article = make_article()
    article.title = "İsrailli bakandan Türkiye açıklaması!"
    article.summary = None
    article.content = "alakasız içerik"
    relevance = NewsService._keyword_relevance(article, NewsService._canonical_terms("israil"))
    assert relevance == 0.9  # 1/1 × 0.9 (title)


def test_keyword_relevance_english_capital_i_not_corrupted_to_turkish_dotless():
    """Düzeltme SADECE Türkçe'ye özgü "İ"yi (U+0130) hedeflemeli, düz ASCII
    "I"ya DOKUNMAMALI — kaynakların 6'sı İngilizce (BBC Technology, TechCrunch
    vb.), "Israel"/"Iran"/"Instagram" gibi kelimelerin baş harfi düz ASCII "I".
    Türkçe'nin büyük noktasız I'sı (İngilizce'de yok) gibi ele alınıp "ı"ya
    çevrilirse İngilizce içerikte kelime baştan bozulur, hiçbir zaman eşleşmez
    — subscriber_matching._tr_lower'ın AKSİNE burada bilinçli olarak farklı
    davranmalı (bkz. news_service.py yorum)."""
    article = make_article()
    article.title = "Israel warns of further escalation"
    article.summary = None
    article.content = "alakasız içerik"
    relevance = NewsService._keyword_relevance(article, NewsService._canonical_terms("israel"))
    assert relevance == 0.9  # 1/1 × 0.9 (title)


# ── _canonical_terms + skor seyreltme regresyonu (18 Ağu 2026'da canlıda bulundu) ──


def test_canonical_terms_uses_stem_not_both_forms():
    """`_tokenize`'ın aksine tek terim/kelime döner — kelime+kök ikisi birden DEĞİL."""
    assert NewsService._canonical_terms("beşiktaşın hocası") == ["beşiktaş", "hoca"]


def test_canonical_terms_no_suffix_unchanged():
    assert NewsService._canonical_terms("yapay zeka") == ["yapay", "zeka"]


def test_canonical_terms_drops_turkish_question_particles():
    """27 Ağu 2026'da RAG canlı QA'sında bulundu: doğal dilli sorularda
    ("israil türkiye savaşı çıkar mı", "alparslan kuytul kim") soru
    parçacıkları ("mı", "kim") hiçbir konu bilgisi taşımadığı halde coverage
    bölenini şişiriyor, gerçekten ilgili haberlerin skorunu yapay olarak
    düşürüyordu. Bunlar SADECE _canonical_terms'ten (relevans skoru) elenir
    — _tokenize (SQL aday havuzu) etkilenmez, zararsız."""
    assert NewsService._canonical_terms("israil türkiye savaşı çıkar mı") == \
        ["israil", "türki", "savaş", "çıkar"]
    assert NewsService._canonical_terms("alparslan kuytul kim") == ["alparslan", "kuytul"]


def test_canonical_terms_question_particle_filter_handles_copula_form():
    """`_TR_SUFFIXES` isim-çekim ekleri içindir, "-dir/-dır" (ek-fiil/copula)
    bunların arasında YOK — yani "nedir" ("ne"+"dir") stemleme ile "ne"ye
    İNMEZ, filtre bu bileşik formu da AYRICA (literal) tanımalı, yoksa
    "yapay zeka nedir" gibi çok sık bir soru kalıbı hâlâ boşuna bölen
    şişirir."""
    assert NewsService._canonical_terms("yapay zeka nedir") == ["yapay", "zeka"]


def test_keyword_relevance_turkish_suffix_does_not_dilute_score():
    """Ekli tek kelimelik sorgu ("beşiktaşın"), kökü ("beşiktaş") ile AYNI skoru vermeli.

    Kök regresyonu: `_tokenize()`'ın ["beşiktaşın","beşiktaş"] çıktısı doğrudan
    `_keyword_relevance`'a verilirse coverage böleni (n=2) şişer, sadece kök
    eşleştiği için skor yapay olarak yarıya düşerdi (0.9 yerine 0.45) — bu da
    canlıda aramayı alakasız sonuçlarla dolduruyordu. `_canonical_terms` ile
    (n=1) skor korunmalı.
    """
    article = make_article()
    article.title = "Beşiktaş'tan flaş transfer kararı"
    article.summary = None

    bare_relevance = NewsService._keyword_relevance(article, NewsService._canonical_terms("beşiktaş"))
    suffixed_relevance = NewsService._keyword_relevance(article, NewsService._canonical_terms("beşiktaşın"))

    assert bare_relevance == suffixed_relevance == 0.9  # 1/1 × 0.9


def test_hybrid_search_turkish_suffixed_query_matches_like_bare_form():
    """Uçtan uca: "beşiktaşın" araması "beşiktaş" ile aynı makaleyi aynı skorla bulmalı."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = []

    article = make_article("https://bbc.com/1")
    article.id = 1
    article.title = "Beşiktaş'tan flaş transfer kararı"
    mock_repo.keyword_search.return_value = [article]

    bare = service.hybrid_search("beşiktaş", n_results=5)
    suffixed = service.hybrid_search("beşiktaşın", n_results=5)

    assert bare[0]["score"] == suffixed[0]["score"]


def test_hybrid_search_ranks_by_coverage():
    """Multi-word query'de daha çok kelime eşleşen article üstte olmalı."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = []

    art_both = make_article("https://bbc.com/1")
    art_both.id = 1
    art_both.title = "Real Madrid haberi"  # 2/2 başlıkta → 0.9

    art_partial = make_article("https://bbc.com/2")
    art_partial.id = 2
    art_partial.title = "Sadece real var"  # 1/2 başlıkta → 0.45

    mock_repo.keyword_search.return_value = [art_partial, art_both]  # sıra önemli değil

    results = service.hybrid_search("real madrid", n_results=5)

    assert len(results) == 2
    assert results[0]["id"] == "1"
    # credibility_score=None -> credibility_factor=0.85: 0.9*0.85, 0.45*0.85
    assert results[0]["score"] == 0.765
    assert results[1]["id"] == "2"
    assert results[1]["score"] == pytest.approx(0.3825)


# ── answer_question (RAG) ────────────────────────────────────────────────────

from src.domain.ports.question_answering_port import QuestionAnsweringError


def make_service_with_qa():
    service, mock_repo, mock_analyzer = make_service()
    mock_qa = MagicMock()
    service.qa_port = mock_qa
    return service, mock_repo, mock_qa


def _evidence_article(article_id, source="BBC", sentiment_label="Neutral", corroboration_count=0):
    a = Article(title=f"Article {article_id}", source=source, url=f"http://x/{article_id}", content="content")
    a.id = article_id
    a.sentiment_label = sentiment_label
    a.corroboration_count = corroboration_count
    return a


def test_answer_question_no_evidence_skips_groq_call():
    """Retrieval boşsa (genel mod) Groq HİÇ ÇAĞRILMAZ + NO_EVIDENCE + suggest_alert=True."""
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("Beşiktaş'ın sağ kanat transferi ne durumda?")
    mock_qa.answer.assert_not_called()
    assert result["coverage"] == "none"
    assert result["suggest_alert"] is True
    assert result["sources"] == []


def test_answer_question_article_mode_invalid_id_returns_none():
    service, mock_repo, mock_qa = make_service_with_qa()
    mock_repo.get_article_by_id.return_value = None
    result = service.answer_question("Bu haberde ne oldu?", article_id=999)
    assert result is None
    mock_qa.answer.assert_not_called()


def test_answer_question_raises_when_qa_port_none():
    """qa_port opsiyonel bağımlılık — None ise anlamlı bir hata (fail-loud)."""
    service, mock_repo, _ = make_service()
    with pytest.raises(QuestionAnsweringError):
        service.answer_question("Ne oldu?")


def test_answer_question_corroboration_level_multi_source():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [
        {"id": "1", "score": 0.9, "source": "BBC"},
        {"id": "2", "score": 0.8, "source": "Sözcü"},
    ]
    mock_repo.get_articles_by_ids.return_value = [
        _evidence_article(1, source="BBC"), _evidence_article(2, source="Sözcü"),
    ]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1, 2]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("Ne oldu?")
    assert result["corroboration_level"] == "multi_source"
    assert mock_qa.answer.call_args.kwargs["corroboration_level"] == "multi_source"


def test_answer_question_corroboration_level_single_source():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1, source="BBC")]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("Ne oldu?")
    assert result["corroboration_level"] == "single_source"


def test_answer_question_ignores_model_answer_when_coverage_none():
    """Model coverage='none' derse 'answer' alanı NE OLURSA OLSUN göz ardı
    edilir, dürüst şablona düşülür (Adım 6, spec)."""
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1)]
    mock_qa.answer.return_value = {"coverage": "none", "answer": "UYDURULMUŞ CEVAP", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("İlgisiz bir soru")
    assert result["answer"] != "UYDURULMUŞ CEVAP"
    assert result["coverage"] == "none"
    assert result["sources"] == []


def test_answer_question_clamps_out_of_range_used_sources():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1)]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1, 99]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("Ne oldu?")
    assert [s["index"] for s in result["sources"]] == [1]


def test_answer_question_article_mode_target_always_included():
    """Habere özel modda hedef, retrieval eşiğinden MUAF — story cluster boş
    dönse bile hedefin kendisi kanıt paketine girer, Groq çağrılır."""
    service, mock_repo, mock_qa = make_service_with_qa()
    target = _evidence_article(5, source="TRT")
    mock_repo.get_article_by_id.return_value = target
    mock_repo.get_articles_by_ids.return_value = [target]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    with patch.object(service, "get_story_cluster", return_value={"article_id": 5, "sources": []}):
        result = service.answer_question("Bu haberde ne oldu?", article_id=5)
    mock_qa.answer.assert_called_once()
    assert result["coverage"] == "full"


def test_answer_question_passes_history_to_qa_port():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1)]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    history = [{"role": "user", "content": "İstanbul'da ne oldu?"}, {"role": "assistant", "content": "..."}]
    with patch.object(service, "hybrid_search", return_value=candidates):
        service.answer_question("Peki ya İzmir'de?", history=history)
    assert mock_qa.answer.call_args.kwargs["history"] == history


def test_answer_question_evidence_includes_article_content():
    """Kanıt paketi artık sadece başlık değil, elimizde olan content'i de
    taşımalı — LLM başlıkta olmayan ama teaser'da geçen detayları görebilsin
    (27 Ağu 2026 canlı bulgusu: 'Trossard kafilede yer almadı' gibi bilgiler
    content'te varken hiç prompt'a girmiyordu)."""
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    article = _evidence_article(1)
    article.content = "Trossard kafilede yer almadı."
    mock_repo.get_articles_by_ids.return_value = [article]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        service.answer_question("Trossard kadroda mı?")
    sources = mock_qa.answer.call_args.kwargs["sources"]
    assert sources[0]["content"] == "Trossard kafilede yer almadı."


def test_answer_question_evidence_content_truncated_to_500_chars():
    """`matched_keyword`'ün zaten kullandığı content[:500] kırpma
    konvansiyonuyla tutarlı — sınırsız uzun bir content prompt'u şişirmesin."""
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    article = _evidence_article(1)
    article.content = "x" * 800
    mock_repo.get_articles_by_ids.return_value = [article]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        service.answer_question("Ne oldu?")
    sources = mock_qa.answer.call_args.kwargs["sources"]
    assert len(sources[0]["content"]) == 500


def test_no_evidence_response_turkish_question_returns_turkish_text():
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("Beşiktaş'ın yeni hocası kim olacak?")
    assert result["answer"] == NewsService._NO_EVIDENCE_TEXT["TR"]


def test_no_evidence_response_english_question_returns_english_text():
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("Who will be the new coach?")
    assert result["answer"] == NewsService._NO_EVIDENCE_TEXT["EN"]


def test_no_evidence_response_ui_language_overrides_char_heuristic():
    """27 Ağu 2026'da canlıda bulundu: kullanıcı TR arayüzdeyken aksansız
    Türkçe yazınca (\"gram altin tekrar cikar mi\" — hiç ğüşıöç yok)
    `_looks_turkish` karakter sezgisi yanlışlıkla EN tahmin ediyordu, site
    TR iken cevap İngilizce geliyordu. Frontend zaten kesin bilinen arayüz
    dilini gönderebiliyor — bu, karakter sezgisinden ÖNCE gelmeli."""
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("gram altin tekrar cikar mi", ui_language="TR")
    assert result["answer"] == NewsService._NO_EVIDENCE_TEXT["TR"]


def test_no_evidence_response_ui_language_none_falls_back_to_heuristic():
    """ui_language verilmezse (ör. eski istemci/doğrudan API kullanımı) eski
    karakter-sezgisi davranışı AYNEN korunur — geriye uyumluluk."""
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("gram altin tekrar cikar mi")
    assert result["answer"] == NewsService._NO_EVIDENCE_TEXT["EN"]


def test_no_evidence_response_invalid_ui_language_falls_back_to_heuristic():
    """Bozuk/tanınmayan bir `ui_language` değeri sessizce göz ardı edilir,
    çökme yerine eski heuristiğe düşülür (fail-open)."""
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("Who will be the new coach?", ui_language="fr-FR")
    assert result["answer"] == NewsService._NO_EVIDENCE_TEXT["EN"]