from src.domain.models.article import Article
from src.domain.models.subscriber import Subscriber
from src.domain.services.subscriber_matching import article_matches_subscriber
from src.domain.topics import TOPICS, VALID_TOPIC_IDS, normalize_topic, topic_label


def test_registry_has_twelve_topics_with_stable_ids_and_other_last():
    ids = [t.id for t in TOPICS]
    assert ids == ["Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World",
                   "Science", "Crypto", "Environment", "Entertainment", "Other"]
    assert VALID_TOPIC_IDS == frozenset(ids)


def test_every_topic_has_tr_and_en_labels():
    for t in TOPICS:
        assert t.labels["TR"] and t.labels["EN"], t.id


def test_topic_label_uses_requested_language_and_falls_back():
    assert topic_label("Science", "TR") == "Bilim"
    assert topic_label("Environment", "EN") == "Environment & Climate"
    assert topic_label("Crypto", "DE") == "Crypto"          # bilinmeyen dil → fallback (EN)
    assert topic_label("Crime", "TR") == "Crime"            # kayıt defterinde olmayan → ham kimlik
    assert topic_label("", "TR") == ""


def test_normalize_topic_maps_anything_invalid_to_other():
    assert normalize_topic("Crypto") == "Crypto"
    for bad in ("Finance", "crypto", "", None, 5, ["Sports"]):
        assert normalize_topic(bad) == "Other"


def test_new_topic_works_in_subscriber_matching():
    art = Article(title="Bitcoin yükseldi", source="CoinDesk", url="u", content="c")
    art.topic = "Crypto"
    assert article_matches_subscriber(art, Subscriber(email="a@b.c", preferred_topics=["Crypto"])) is True
    assert article_matches_subscriber(art, Subscriber(email="a@b.c", preferred_topics=["Sports"])) is False


def test_topic_is_hashable_and_registry_is_immutable():
    """Kayıt defteri tek doğruluk kaynağı: hiçbir çağıran etiketleri sessizce değiştirememeli,
    ve `frozen` bir kayıt küme/sözlük anahtarı olarak kullanılabilmeli (inceleme bulgusu)."""
    import pytest
    assert len({t for t in TOPICS}) == len(TOPICS)          # hash(Topic) çökmemeli
    with pytest.raises(TypeError):
        TOPICS[0].labels["TR"] = "değiştirildi"
    assert topic_label("Technology", "TR") == "Teknoloji"
