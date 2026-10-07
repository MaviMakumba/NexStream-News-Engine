from src.domain.models.article import Article
from src.domain.models.subscriber import Subscriber
from src.domain.services.subscriber_matching import (
    matched_keyword,
    has_preferences,
    article_matches_subscriber,
)


def _article(title="Beşiktaş kazandı", topic="Sports", source="TRT"):
    a = Article(title=title, source=source, url="http://t.com", content="Beşiktaş, Fenerbahçe'yi yendi.")
    a.summary = "Maç özeti"
    a.topic = topic
    return a


def _subscriber(keywords=None, preferred_topics=None, preferred_sources=None):
    return Subscriber(
        email="fan@test.com",
        keywords=keywords or [],
        preferred_topics=preferred_topics or [],
        preferred_sources=preferred_sources or [],
    )


# ── matched_keyword ─────────────────────────────────────────────────────────

def _tren_article(title, content="içerik"):
    a = Article(title=title, source="HT Spor", url="http://t.com/x", content=content)
    a.summary = ""
    return a


def test_keyword_does_not_match_words_that_merely_start_with_it():
    """29 Eyl 2026 kullanıcı bulgusu: 'tren' anahtar kelimesi bülten e-postasında
    'Trendyol 1. Lig' / 'Trendyol Süper Lig' haberlerini yakaladı (önek eşleşmesi).
    Kalan parça çekim eki DEĞİLSE ('dyol', 'd') eşleşme olmamalı."""
    assert matched_keyword(_tren_article("Mardin 1969 Spor, Petev'le imzaladı!",
                                         "Trendyol 1. Lig ekiplerinden Mardin 1969 Spor..."), ["tren"]) is None
    assert matched_keyword(_tren_article("G.Saray'da Kasımpaşa maçı mesaisi!",
                                         "Trendyol Süper Lig’in 7. haftasında Kasımpaşa ile..."), ["tren"]) is None
    assert matched_keyword(_tren_article("Yeni trend: kısa video"), ["tren"]) is None


def test_keyword_still_matches_real_inflections():
    """Çekimler yakalanmaya devam etmeli: mevcut aboneler bu yüzden 'tren' seçti."""
    for title in ("Hızlı tren seferleri başladı", "Trenler rötarlı", "Trenin motoru arızalandı",
                  "Trene yeni vagon eklendi", "Trende yangın çıktı", "Trenlerden inen yolcular",
                  "Tren'in bileti", "Trenlerimizdeki yolcular", "TREN kazası"):
        assert matched_keyword(_tren_article(title), ["tren"]) == "tren", title


def test_keyword_multiword_phrase_last_word_must_be_inflection():
    a = _tren_article("Gram altın rekor kırdı")
    assert matched_keyword(a, ["gram altın"]) == "gram altın"
    assert matched_keyword(_tren_article("Gram altınlar yükseldi"), ["gram altın"]) == "gram altın"
    assert matched_keyword(_tren_article("Gram altıncı çeyrek"), ["gram altın"]) is None


def test_keyword_english_plural_still_matches():
    """Kaynakların yarısı İngilizce: 'tesla' → 'teslas' ya da 'apple' → 'apples' çoğulu."""
    assert matched_keyword(_tren_article("Apples and oranges"), ["apple"]) == "apple"
    assert matched_keyword(_tren_article("Applet is a small program"), ["apple"]) is None


def test_city_keyword_still_matches_its_football_club():
    """'kocaeli' takip eden biri Kocaelispor haberini de ister — tek bir dilbilgisi
    kuralı (-spor bileşiği), şehir başına liste değil."""
    assert matched_keyword(_tren_article("Kocaelispor'dan sakatlık açıklaması!"), ["kocaeli"]) == "kocaeli"
    assert matched_keyword(_tren_article("Sakaryaspor kazandı"), ["sakarya"]) == "sakarya"


def test_keyword_exact_brand_still_matches_itself():
    assert matched_keyword(_tren_article("Trendyol yeni kampanya başlattı"), ["trendyol"]) == "trendyol"


def test_matched_keyword_finds_match_in_title():
    assert matched_keyword(_article(), ["beşiktaş"]) == "beşiktaş"


def test_matched_keyword_case_insensitive():
    """Fonksiyon kendi içinde küçültme yapar — çağıran taraf önceden .lower() çağırmamalı,
    aksi halde Türkçe 'İ' (U+0130) Python'un varsayılan .lower()'ında "i̇" (birleşen işaretli)
    olur ve eşleşme kaçar; ham "İ" girdisiyle test etmek gerçek kullanım senaryosunu yansıtır."""
    assert matched_keyword(_article(), ["BEŞİKTAŞ"]) is not None


def test_matched_keyword_returns_none_when_no_match():
    assert matched_keyword(_article(), ["galatasaray"]) is None


def test_matched_keyword_returns_none_for_empty_list():
    assert matched_keyword(_article(), []) is None


def test_matched_keyword_returns_first_match():
    assert matched_keyword(_article(), ["galatasaray", "beşiktaş", "fenerbahçe"]) == "beşiktaş"


def test_matched_keyword_does_not_match_mid_word_substring():
    """26 Ağu 2026 bug: 'altın' tek başına 'gözaltına alındı' içinde ham substring
    olarak geçiyordu (göz+ALTINa) — kelime sınırı olmadan hiçbir dilbilgisel
    ilişkisi yokken eşleşiyordu. Aynı bug sınıfı news_service._keyword_relevance'ta
    zaten düzeltilmişti (\"Adana\"/\"havadan\"), burada da aynı desen gerekiyor."""
    article = _article(title="Şüpheli gözaltına alındı", topic="Crime")
    assert matched_keyword(article, ["altın"]) is None


def test_matched_keyword_still_matches_inflected_suffix():
    """Kelime sınırı SADECE baştan sabitlenmeli — çekim eklerini (ör. 'altının')
    hâlâ yakalamalı, aksi halde meşru Türkçe kullanım kaybolur."""
    article = _article(title="Gram altının fiyatı yükseldi", topic="Economy")
    assert matched_keyword(article, ["altın"]) == "altın"


def test_matched_keyword_does_not_match_false_friend_altinda():
    """27 Ağu 2026 bug: 'altın' (gold) kökü 'altında'/'altındaki' ("alt" [under]
    kelimesinin çekimli hali, "altı" + buffer "n" + "da/daki") ile harf
    düzeyinde çakışıyor — 'İşgal altındaki topraklar' gibi altınla hiç ilgisi
    olmayan bir haber 'altın' uyarısını tetikliyordu. Bu ikisi gerçek
    morfolojik analiz olmadan ayırt edilemez (aynı harfler), bu yüzden bilinen
    çakışan tam kelimeler için küçük bir istisna listesi (_FALSE_FRIEND_WORDS)
    gerekiyor — \\b-anchor tek başına yetmiyor çünkü 'altında' önünde gerçek
    bir kelime sınırı var (bkz. gözaltı bug'ından farkı)."""
    article = _article(title="İşgal altındaki topraklarda gerginlik sürüyor", topic="World")
    assert matched_keyword(article, ["altın"]) is None

    article2 = _article(title="Baskı altında geçen bir yıl", topic="Politics")
    assert matched_keyword(article2, ["altın"]) is None


def test_matched_keyword_false_friend_does_not_block_real_gold_locative():
    """İstisna sadece BİLİNEN çakışan tam kelimeleri engellemeli — 'altın'ın
    kendi çekimli hallerinden biri değilse (ör. 'altını', 'altınla') hâlâ
    normal şekilde eşleşmeli."""
    article = _article(title="Altını çeyrek çeyrek biriktirenler kazandı", topic="Economy")
    assert matched_keyword(article, ["altın"]) == "altın"


def test_matched_keyword_multi_word_phrase_requires_exact_sequence():
    """Çok kelimeli bir keyword ('gram altın') ifadenin YAN YANA geçmesini
    gerektirmeli — sadece bileşenlerinden biri geçmesi yetmemeli."""
    article = _article(title="Gram altın rekor kırdı", topic="Economy")
    assert matched_keyword(article, ["gram altın"]) == "gram altın"

    unrelated = _article(title="Altın kupa Beşiktaş'ta, gram et fiyatları da arttı", topic="Economy")
    assert matched_keyword(unrelated, ["gram altın"]) is None


# ── has_preferences ────────────────────────────────────────────────────────

def test_has_preferences_false_when_all_empty():
    assert has_preferences(_subscriber()) is False


def test_has_preferences_true_with_keywords():
    assert has_preferences(_subscriber(keywords=["nato"])) is True


def test_has_preferences_true_with_topics():
    assert has_preferences(_subscriber(preferred_topics=["Sports"])) is True


def test_has_preferences_true_with_sources():
    assert has_preferences(_subscriber(preferred_sources=["TRT"])) is True


# ── article_matches_subscriber ───────────────────────────────────────────────

def test_matches_by_topic():
    sub = _subscriber(preferred_topics=["Sports"])
    assert article_matches_subscriber(_article(topic="Sports"), sub) is True


def test_does_not_match_different_topic():
    sub = _subscriber(preferred_topics=["Politics"])
    assert article_matches_subscriber(_article(topic="Sports"), sub) is False


def test_matches_by_source():
    sub = _subscriber(preferred_sources=["TRT"])
    assert article_matches_subscriber(_article(source="TRT"), sub) is True


def test_matches_by_keyword():
    sub = _subscriber(keywords=["beşiktaş"])
    assert article_matches_subscriber(_article(topic="Politics", source="Other"), sub) is True


def test_matches_when_any_one_criterion_matches():
    """Konu/kaynak/keyword arasında OR mantığı — biri tutarsa yeterli."""
    sub = _subscriber(preferred_topics=["Politics"], keywords=["beşiktaş"])
    assert article_matches_subscriber(_article(topic="Sports"), sub) is True


def test_no_match_when_nothing_matches():
    sub = _subscriber(preferred_topics=["Politics"], preferred_sources=["Habertürk"], keywords=["nato"])
    assert article_matches_subscriber(_article(topic="Sports", source="TRT"), sub) is False


# ── Eşleşme metni kapsamı (7 Eki 2026 mutasyon denetimi) ─────────────────────

def test_matched_keyword_looks_into_summary():
    a = Article(title="Gündem", source="TRT", url="u", content="içerik")
    a.summary = "Borsada rekor beklentisi"
    assert matched_keyword(a, ["borsa"]) == "borsa"


def test_matched_keyword_only_reads_first_500_content_characters():
    # "x" tam sınırda: indeks 499 içeride, 500 dışarıda
    inside = Article(title="t", source="TRT", url="u", content="a" * 498 + " x")
    outside = Article(title="t", source="TRT", url="u", content="a" * 499 + " x")
    assert matched_keyword(inside, ["x"]) == "x"
    assert matched_keyword(outside, ["x"]) is None


def test_matched_keyword_returns_none_not_false_when_nothing_matches():
    assert matched_keyword(_tren_article("Trendyol Süper Lig"), ["tren"]) is None
