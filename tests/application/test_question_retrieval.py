"""Doğal dilli soruda arama kalitesi (16 Eki 2026, "Beşiktaş Avrupa Ligi'nde kaç gol attı").

Canlıda bulunan iki kök neden:
1. Soru çerçevesi sözcükleri ("kaçıncı", "kaçta") skor bölenini şişiriyor ve SQL
   aday havuzuna `%kac%` gibi alt dizilerle çöp haber sokuyordu.
2. Konuyu belirleyen terim ("beşiktaş") küçük harfle yazılınca özel isim sayılmıyor,
   "gol/lig/avrupa" gibi genel kelimelerle EŞİT ağırlıkta kalıyordu.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.application.services.news_service import NewsService
from src.domain.models.article import Article
from src.domain.services.turkish_morphology import is_question_word

QUESTION = "beşiktaş avrupa liginde kaçıncı sırada kaç gol attı"


@pytest.fixture(autouse=True)
def _fresh_vocabulary():
    NewsService.reset_entity_vocabulary_cache()
    yield
    NewsService.reset_entity_vocabulary_cache()


def _service(entity_articles=()):
    repo = MagicMock()
    repo.get_recent_articles_with_entities.return_value = list(entity_articles)
    repo.keyword_search.return_value = []
    repo.get_articles_by_ids.return_value = []
    return NewsService(repository=repo, analyzer=MagicMock()), repo


def _entity_article(**entities):
    return Article(title="t", source="s", url="u", content="c", entities=entities)


# ── soru çerçevesi sözcükleri (kapalı sınıf: soru kökü + çekim/sıra eki) ──────

@pytest.mark.parametrize("word", ["kaç", "kaçıncı", "kaçta", "hangi", "hangisi", "nasıl",
                                  "neden", "nerede", "neresi", "niçin", "niye"])
def test_question_frame_words_are_recognised(word):
    assert is_question_word(word)


@pytest.mark.parametrize("word", ["kaçak", "kaçırıldı", "kimya", "net", "haber", "beşiktaş", "gol"])
def test_content_words_are_not_question_words(word):
    assert not is_question_word(word)


def test_canonical_terms_drop_question_frame_words():
    terms = NewsService._canonical_terms(QUESTION)
    assert terms == ["beşiktaş", "avrupa", "lig", "sıra", "gol", "att"]


def test_canonical_terms_keep_kacak_as_content_word():
    assert "kaçak" in NewsService._canonical_terms("kaçak göçmen haberi")


# ── varlık (anchor) terimleri: küçük harfle yazılsa da bilinen bir varlığı adlandırır ──

def test_anchor_terms_come_from_known_single_word_entities():
    service, _ = _service([_entity_article(organizations=["Beşiktaş", "Şampiyonlar Ligi"],
                                           locations=["Avrupa"])])
    assert service._query_anchor_terms(QUESTION) == ["beşiktaş", "avrupa"]


def test_anchor_terms_ignore_words_only_part_of_multiword_entity():
    # "lig" yalnızca "Şampiyonlar Ligi"nin parçası — tek başına varlık adı değil.
    service, _ = _service([_entity_article(organizations=["Şampiyonlar Ligi"])])
    assert service._query_anchor_terms("lig puan durumu") == []


def test_anchor_terms_include_capitalized_words_without_vocabulary():
    service, _ = _service()
    assert service._query_anchor_terms("Hoffenheim maçı kaç kaç bitti") == ["hoffenheim"]


def test_anchor_vocabulary_failure_is_fail_open():
    service, repo = _service()
    repo.get_recent_articles_with_entities.side_effect = RuntimeError("db down")
    assert service._query_anchor_terms(QUESTION) == []


def test_anchor_vocabulary_is_cached_between_queries():
    service, repo = _service([_entity_article(organizations=["Beşiktaş"])])
    service._query_anchor_terms(QUESTION)
    service._query_anchor_terms(QUESTION)
    assert repo.get_recent_articles_with_entities.call_count == 1


def test_anchor_terms_never_include_question_frame_words():
    service, _ = _service([_entity_article(organizations=["Kaç"])])
    assert service._query_anchor_terms("kaç gol attı") == []


# ── ağırlıklı kapsama: konu terimi genel kelimelerden ağır basar ─────────────

def _relevance(article, anchors):
    return NewsService._keyword_relevance(
        article, NewsService._canonical_terms(QUESTION), anchors=frozenset(anchors))


def test_anchor_match_outweighs_generic_word_matches():
    on_topic = Article(title="Hoffenheim 2-3 Beşiktaş maç özeti", source="s", url="u1",
                       content="Kartal Almanya'da kazandı")
    generic = Article(title="Şampiyonlar Ligi'nde en gollü hafta rekoru", source="s", url="u2",
                      content="Avrupa'da gol yağmuru, lig tarihinin rekoru")
    assert _relevance(on_topic, {"beşiktaş"}) > _relevance(generic, {"beşiktaş"})


def test_without_anchors_scoring_is_unchanged():
    article = Article(title="Beşiktaş kazandı", source="s", url="u", content="x")
    terms = NewsService._canonical_terms("beşiktaş gol")
    assert NewsService._keyword_relevance(article, terms) == \
        NewsService._keyword_relevance(article, terms, anchors=frozenset())


# ── aday havuzu: anchor terimleri için AYRI sorgu (genel kelimeler havuzu doldurmasın) ──

def test_hybrid_search_pulls_anchor_articles_with_dedicated_query():
    service, repo = _service([_entity_article(organizations=["Beşiktaş"])])
    service.hybrid_search(QUESTION, n_results=8)
    pool_terms = [c.kwargs.get("terms") for c in repo.keyword_search.call_args_list]
    assert ["beşiktaş"] in pool_terms


def test_hybrid_search_without_anchors_makes_single_keyword_query():
    service, repo = _service()
    service.hybrid_search("yapay zeka", n_results=8)
    assert repo.keyword_search.call_count == 1


def test_anchor_article_surfaces_even_when_generic_pool_is_junk():
    on_topic = Article(title="Hoffenheim 2-3 Beşiktaş maç özeti", source="Dünya", url="u1",
                       content="Kartal Almanya'da kazandı", id=1, created_at=datetime.now(timezone.utc))
    junk = Article(title="Tesla Roadster uçtu", source="TC", url="u2", content="attı", id=2,
                   created_at=datetime.now(timezone.utc))
    service, repo = _service([_entity_article(organizations=["Beşiktaş"])])

    def fake_keyword_search(query, limit, source=None, sentiment=None, terms=None):
        return [on_topic] if terms == ["beşiktaş"] else [junk]
    repo.keyword_search.side_effect = fake_keyword_search
    repo.get_articles_by_ids.return_value = [on_topic, junk]

    results = service.hybrid_search(QUESTION, n_results=8)
    assert results and results[0]["id"] in (1, "1")
