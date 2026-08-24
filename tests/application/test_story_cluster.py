"""NewsService.get_story_cluster testleri (v2.2, "bu haberi kim nasıl anlatıyor").

`get_related` (entity kesişimi) ile aynı dosya deseni — search_repository
mock'lanır, saf orkestrasyon doğrulanır (asıl benzerlik hesabı ChromaSearchRepository'de).
"""

from unittest.mock import MagicMock
from src.application.services.news_service import NewsService


def _service(search_repository=None):
    repo = MagicMock()
    return NewsService(repository=repo, analyzer=MagicMock(), search_repository=search_repository), repo


def test_story_cluster_returns_sources_from_search_repository():
    from src.domain.models.article import Article

    search_repo = MagicMock()
    search_repo.find_similar.return_value = [
        {"id": 2, "title": "Başka kaynak", "source": "TRT", "url": "u2", "score": 0.81},
    ]
    service, repo = _service(search_repo)
    # entities=None → hedefin ayırt edici entity'si yok, semantik doğrulama atlanır
    # (bkz. test_story_cluster_keeps_semantic_matches_when_target_has_no_entities)
    repo.get_article_by_id.return_value = Article(id=1, title="t", source="X", url="u1", content="c", entities=None)

    result = service.get_story_cluster(1, limit=6)

    assert result == {"article_id": 1, "sources": [
        {"id": 2, "title": "Başka kaynak", "source": "TRT", "url": "u2", "score": 0.81},
    ]}
    search_repo.find_similar.assert_called_once_with(1, n_results=6)


def test_story_cluster_empty_when_no_search_repository():
    """ChromaDB opsiyonel (search_repository=None) — özellik sessizce devre dışı kalır."""
    service, _ = _service(search_repository=None)
    assert service.get_story_cluster(1) == {"article_id": 1, "sources": []}


# ── Rozet/panel tutarlılık regresyonu (20 Ağu 2026'da canlıda bulundu) ────────
# Kart "N kaynak doğruluyor" (corroboration_count = entity-overlap) diyordu ama
# panel SADECE semantik embedding eşiğine (0.72) bakıyordu — ikisi asla aynı
# şeyi ölçmediği için rozet "2 kaynak" derken panel boş kalabiliyordu.

def test_story_cluster_falls_back_to_entity_overlap_when_semantic_finds_nothing():
    """Semantik arama boş dönse bile (`find_similar` eşiği tutmadı), rozetin
    saydığı (entity-overlap) kaynak panelde HER ZAMAN görünmeli."""
    from src.domain.models.article import Article

    search_repo = MagicMock()
    search_repo.find_similar.return_value = []  # embedding eşiği tutmadı

    repo = MagicMock()
    two_entities = {"persons": ["Erdogan"], "organizations": ["NATO"], "locations": []}
    target = Article(id=1, title="Hedef haber", source="BBC", url="u1", content="c", entities=two_entities)
    corroborating = Article(id=2, title="Farklı kelimelerle aynı olay", source="TRT", url="u2",
                             content="c", entities=two_entities)
    repo.get_article_by_id.return_value = target
    repo.get_recent_articles_with_entities.return_value = [corroborating]

    service = NewsService(repository=repo, analyzer=MagicMock(), search_repository=search_repo)
    result = service.get_story_cluster(1, limit=6)

    assert result["sources"] == [
        {"id": 2, "title": "Farklı kelimelerle aynı olay", "source": "TRT", "url": "u2", "score": 1.0},
    ]


def test_story_cluster_merges_semantic_and_entity_overlap_without_duplicates():
    """Aynı makale hem semantik hem entity-overlap ile bulunursa bir kez görünmeli
    (semantik sonuç kazanır — zaten gerçek bir skoru var)."""
    from src.domain.models.article import Article

    search_repo = MagicMock()
    search_repo.find_similar.return_value = [
        {"id": 2, "title": "Aynı makale (semantik)", "source": "TRT", "url": "u2", "score": 0.81},
    ]

    repo = MagicMock()
    two_entities = {"persons": ["Erdogan"], "organizations": ["NATO"], "locations": []}
    target = Article(id=1, title="Hedef haber", source="BBC", url="u1", content="c", entities=two_entities)
    same_as_semantic = Article(id=2, title="Aynı makale (entity)", source="TRT", url="u2",
                                content="c", entities=two_entities)
    repo.get_article_by_id.return_value = target
    repo.get_recent_articles_with_entities.return_value = [same_as_semantic]
    repo.get_articles_by_ids.return_value = [same_as_semantic]  # semantik doğrulama bu id'yi çeker

    service = NewsService(repository=repo, analyzer=MagicMock(), search_repository=search_repo)
    result = service.get_story_cluster(1, limit=6)

    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Aynı makale (semantik)"  # semantik veri kazandı


# ── Semantik eşleşmelerin entity doğrulaması (24 Ağu 2026'da canlıda bulundu) ─
# Kısa/kalıplaşmış haber şablonlarında ("X'de orman yangını çıktı") embedding
# benzerliği FARKLI gerçek olayları aynı "story" sayabiliyordu. Canlıda: Ankara'daki
# bir yangın haberi, Kaş/Kemer/Bursa/Uludağ'daki alakasız yangınlarla (hiçbir entity
# paylaşmadıkları halde) skor 0.72-0.92 arasında eşleşti.

def test_story_cluster_filters_semantic_matches_without_entity_overlap():
    """Semantik eşleşme hedefle HİÇ entity paylaşmıyorsa (farklı gerçek olay,
    sadece kalıp-cümle benzerliği) elenir."""
    from src.domain.models.article import Article

    search_repo = MagicMock()
    search_repo.find_similar.return_value = [
        {"id": 2, "title": "Alakasız başka bir yangın", "source": "TRT", "url": "u2", "score": 0.81},
    ]

    repo = MagicMock()
    target = Article(id=1, title="Ankara'da yangın", source="BBC", url="u1", content="c",
                      entities={"persons": [], "organizations": ["Ankara Valiliği"], "locations": ["Ankara", "Mamak"]})
    unrelated = Article(id=2, title="Alakasız başka bir yangın", source="TRT", url="u2", content="c",
                         entities={"persons": [], "organizations": [], "locations": ["Bursa"]})
    repo.get_article_by_id.return_value = target
    repo.get_recent_articles_with_entities.return_value = []
    repo.get_articles_by_ids.return_value = [unrelated]

    service = NewsService(repository=repo, analyzer=MagicMock(), search_repository=search_repo)
    result = service.get_story_cluster(1, limit=6)

    assert result["sources"] == []


def test_story_cluster_keeps_semantic_matches_with_entity_overlap():
    """Semantik eşleşme hedefle en az bir ayırt edici entity paylaşıyorsa
    (farklı kelimelerle anlatılan AYNI olay) korunur."""
    from src.domain.models.article import Article

    search_repo = MagicMock()
    search_repo.find_similar.return_value = [
        {"id": 2, "title": "Farklı kelimelerle aynı yangın", "source": "TRT", "url": "u2", "score": 0.91},
    ]

    repo = MagicMock()
    target = Article(id=1, title="Ankara'da yangın", source="BBC", url="u1", content="c",
                      entities={"persons": [], "organizations": ["Ankara Valiliği"], "locations": ["Ankara", "Mamak"]})
    same_event = Article(id=2, title="Farklı kelimelerle aynı yangın", source="TRT", url="u2", content="c",
                          entities={"persons": [], "organizations": ["Ankara Valiliği"], "locations": ["Ankara", "Mamak"]})
    repo.get_article_by_id.return_value = target
    repo.get_recent_articles_with_entities.return_value = []
    repo.get_articles_by_ids.return_value = [same_event]

    service = NewsService(repository=repo, analyzer=MagicMock(), search_repository=search_repo)
    result = service.get_story_cluster(1, limit=6)

    assert result["sources"] == [
        {"id": 2, "title": "Farklı kelimelerle aynı yangın", "source": "TRT", "url": "u2", "score": 0.91},
    ]


def test_story_cluster_keeps_semantic_matches_when_target_has_no_entities():
    """Hedefin hiç ayırt edici entity'si yoksa (ör. NER hiçbir şey çıkaramadı)
    semantik doğrulama atlanır — hepsini elemek, hiç doğrulayamamaktan daha
    kötü bir varsayılan olurdu. Gereksiz `get_articles_by_ids` sorgusu da atılmamalı."""
    from src.domain.models.article import Article

    search_repo = MagicMock()
    search_repo.find_similar.return_value = [
        {"id": 2, "title": "Bir eşleşme", "source": "TRT", "url": "u2", "score": 0.81},
    ]

    repo = MagicMock()
    target = Article(id=1, title="Entity'siz haber", source="BBC", url="u1", content="c",
                      entities={"persons": [], "organizations": [], "locations": []})
    repo.get_article_by_id.return_value = target
    repo.get_recent_articles_with_entities.return_value = []

    service = NewsService(repository=repo, analyzer=MagicMock(), search_repository=search_repo)
    result = service.get_story_cluster(1, limit=6)

    assert result["sources"] == [
        {"id": 2, "title": "Bir eşleşme", "source": "TRT", "url": "u2", "score": 0.81},
    ]
    repo.get_articles_by_ids.assert_not_called()
