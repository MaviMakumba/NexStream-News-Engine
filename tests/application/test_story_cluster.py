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
    search_repo = MagicMock()
    search_repo.find_similar.return_value = [
        {"id": 2, "title": "Başka kaynak", "source": "TRT", "url": "u2", "score": 0.81},
    ]
    service, _ = _service(search_repo)

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

    service = NewsService(repository=repo, analyzer=MagicMock(), search_repository=search_repo)
    result = service.get_story_cluster(1, limit=6)

    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Aynı makale (semantik)"  # semantik veri kazandı
