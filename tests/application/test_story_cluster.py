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
