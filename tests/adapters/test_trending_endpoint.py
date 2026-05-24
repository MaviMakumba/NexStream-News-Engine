import pytest
from unittest.mock import MagicMock
from src.application.services.news_service import NewsService
from src.domain.models.article import Article


def make_article(title="Test", entities=None, topic="Technology", url="https://x.com/1"):
    return Article(
        id=1,
        title=title,
        source="BBC",
        url=url,
        content="Content",
        entities=entities,
        topic=topic,
    )


def make_service():
    mock_repo = MagicMock()
    mock_analyzer = MagicMock()
    return NewsService(repository=mock_repo, analyzer=mock_analyzer), mock_repo


def test_trending_returns_most_frequent_entities():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = [
        make_article("H1", {"persons": ["Erdogan", "Biden"], "organizations": ["UN"], "locations": ["Ankara"]}, url="u1"),
        make_article("H2", {"persons": ["Erdogan"], "organizations": ["NATO"], "locations": ["Ankara"]}, url="u2"),
        make_article("H3", {"persons": ["Erdogan"], "organizations": ["UN"], "locations": []}, url="u3"),
    ]

    result = service.get_trending(hours=6, limit=3)

    assert result["hours"] == 6
    entities = result["entities"]
    names = [e["name"] for e in entities]
    assert entities[0]["name"] == "Erdogan"
    assert entities[0]["count"] == 3
    assert len(entities) == 3


def test_trending_returns_entity_type():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = [
        make_article("H1", {"persons": ["Ali"], "organizations": ["Google"], "locations": ["Istanbul"]}),
    ]

    result = service.get_trending(hours=6, limit=10)

    type_map = {e["name"]: e["type"] for e in result["entities"]}
    assert type_map["Ali"] == "person"
    assert type_map["Google"] == "organization"
    assert type_map["Istanbul"] == "location"


def test_trending_includes_example_titles():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = [
        make_article("Haber A", {"persons": ["Ahmet"], "organizations": [], "locations": []}, url="u1"),
        make_article("Haber B", {"persons": ["Ahmet"], "organizations": [], "locations": []}, url="u2"),
    ]

    result = service.get_trending(hours=6, limit=5)

    entity = result["entities"][0]
    assert entity["name"] == "Ahmet"
    assert "Haber A" in entity["example_titles"]
    assert "Haber B" in entity["example_titles"]


def test_trending_limits_example_titles_to_3():
    service, mock_repo = make_service()
    articles = [
        make_article(f"Title {i}", {"persons": ["Popular Entity"], "organizations": [], "locations": []}, url=f"u{i}")
        for i in range(5)
    ]
    mock_repo.get_recent_articles_with_entities.return_value = articles

    result = service.get_trending(hours=6, limit=5)

    assert len(result["entities"][0]["example_titles"]) == 3


def test_trending_empty_when_no_articles():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = []

    result = service.get_trending(hours=6, limit=10)

    assert result["entities"] == []
    assert result["hours"] == 6


def test_trending_skips_articles_without_entities():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = [
        make_article("H1", None, url="u1"),
        make_article("H2", {"persons": ["Ali"], "organizations": [], "locations": []}, url="u2"),
    ]

    result = service.get_trending(hours=6, limit=10)

    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Ali"


def test_trending_respects_limit():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = [
        make_article("H", {
            "persons": ["Ahmet", "Mehmet", "Ayse", "Fatma", "Zeynep"],
            "organizations": [],
            "locations": [],
        }),
    ]

    result = service.get_trending(hours=6, limit=2)

    assert len(result["entities"]) == 2


def test_trending_passes_hours_to_repository():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = []

    service.get_trending(hours=12, limit=5)

    mock_repo.get_recent_articles_with_entities.assert_called_once_with(12)


def test_trending_skips_short_entity_names():
    service, mock_repo = make_service()
    mock_repo.get_recent_articles_with_entities.return_value = [
        make_article("H1", {"persons": ["X", "Ali"], "organizations": [], "locations": []}),
    ]

    result = service.get_trending(hours=6, limit=10)

    names = [e["name"] for e in result["entities"]]
    assert "X" not in names
    assert "Ali" in names
