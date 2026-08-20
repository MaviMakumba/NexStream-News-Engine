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


def test_hybrid_search_returns_semantic_results():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Semantic Haber", "summary": "s", "source": "BBC", "url": "u", "score": 0.9,
         "published_at": datetime.now(timezone.utc).isoformat()}
    ]
    mock_repo.keyword_search.return_value = []

    results = service.hybrid_search("yapay zeka", n_results=5)

    assert len(results) == 1
    assert results[0]["score"] == 0.9
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
    assert results[0]["score"] == 0.90


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
    assert results[0]["score"] == 0.90  # "fallback" başlıkta → 0.90


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
    # max(sem=0.6, kw=0.9) + bonus=0.10 = 1.0 (cap)
    assert results[0]["score"] == 1.0


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
    assert results[0]["score"] == 0.90
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
    assert scores[2] == pytest.approx(0.5, abs=0.001)       # very_old: relevance(1.0) * floor(0.5)


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


# ── _canonical_terms + skor seyreltme regresyonu (18 Ağu 2026'da canlıda bulundu) ──


def test_canonical_terms_uses_stem_not_both_forms():
    """`_tokenize`'ın aksine tek terim/kelime döner — kelime+kök ikisi birden DEĞİL."""
    assert NewsService._canonical_terms("beşiktaşın hocası") == ["beşiktaş", "hoca"]


def test_canonical_terms_no_suffix_unchanged():
    assert NewsService._canonical_terms("yapay zeka") == ["yapay", "zeka"]


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
    assert results[0]["score"] == 0.9
    assert results[1]["id"] == "2"
    assert results[1]["score"] == 0.45