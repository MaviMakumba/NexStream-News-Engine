from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.application.services.news_service import NewsService
from src.domain.models.article import Article


def _service():
    repo = MagicMock()
    return NewsService(repository=repo, analyzer=MagicMock()), repo


def _art(article_id, title, entities, source="BBC", created=None):
    return Article(
        id=article_id, title=title, source=source, url=f"u{article_id}", content="c",
        entities=entities,
        created_at=created or datetime(2026, 5, 1, tzinfo=timezone.utc),
    )


def test_related_returns_articles_sharing_entities_sorted_by_overlap():
    service, repo = _service()
    repo.get_article_by_id.return_value = _art(
        1, "Target", {"persons": ["Erdogan"], "organizations": ["NATO"], "locations": []})
    repo.get_articles_with_entities.return_value = [
        _art(2, "Shares two", {"persons": ["Erdogan"], "organizations": ["NATO"], "locations": []}),
        _art(3, "Shares one", {"persons": ["Erdogan"], "organizations": [], "locations": []}),
        _art(4, "Shares none", {"persons": ["Biden"], "organizations": [], "locations": []}),
    ]

    result = service.get_related(1, limit=5)

    assert result["article_id"] == 1
    related = result["related"]
    assert [r["id"] for r in related] == [2, 3]
    assert related[0]["overlap"] == 2
    assert related[1]["overlap"] == 1


def test_related_empty_when_article_not_found():
    service, repo = _service()
    repo.get_article_by_id.return_value = None

    result = service.get_related(99)

    assert result == {"article_id": 99, "related": []}
    repo.get_articles_with_entities.assert_not_called()


def test_related_empty_when_target_has_no_entities():
    service, repo = _service()
    repo.get_article_by_id.return_value = _art(1, "No entities", None)

    assert service.get_related(1)["related"] == []


def test_related_respects_limit():
    service, repo = _service()
    repo.get_article_by_id.return_value = _art(
        1, "T", {"persons": ["X1", "X2"], "organizations": [], "locations": []})
    repo.get_articles_with_entities.return_value = [
        _art(i, f"A{i}", {"persons": ["X1", "X2"], "organizations": [], "locations": []})
        for i in range(2, 10)
    ]

    assert len(service.get_related(1, limit=3)["related"]) == 3


def test_related_preserves_target_entity_casing():
    service, repo = _service()
    repo.get_article_by_id.return_value = _art(
        1, "T", {"persons": ["Erdoğan"], "organizations": ["NATO"], "locations": []})
    repo.get_articles_with_entities.return_value = [
        _art(2, "A", {"persons": ["erdoğan"], "organizations": ["nato"], "locations": []}),
    ]

    shared = service.get_related(1)["related"][0]["shared_entities"]
    assert "Erdoğan" in shared
    assert "NATO" in shared


def test_related_passes_exclude_id_to_repository():
    service, repo = _service()
    repo.get_article_by_id.return_value = _art(
        1, "T", {"persons": ["Apple", "Boeing"], "organizations": [], "locations": []})
    repo.get_articles_with_entities.return_value = []

    service.get_related(1, limit=5)

    repo.get_articles_with_entities.assert_called_once_with(limit=500, exclude_id=1)
