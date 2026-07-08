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
