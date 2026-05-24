import pytest
from unittest.mock import MagicMock, patch
from src.adapters.search.chroma_search_repository import ChromaSearchRepository
from src.domain.models.article import Article


def make_article(**kwargs):
    defaults = dict(
        id=1,
        title="Test Haberi",
        source="BBC",
        url="https://bbc.com/test",
        content="Bu bir test haberidir.",
        summary="Kısa özet.",
        sentiment_label="Neutral",
        sentiment_score=0.0,
    )
    defaults.update(kwargs)
    return Article(**defaults)


def make_repo():
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 384

    with patch("src.adapters.search.chroma_search_repository.chromadb.HttpClient") as mock_client_cls:
        mock_collection = MagicMock()
        mock_client_cls.return_value.get_or_create_collection.return_value = mock_collection
        repo = ChromaSearchRepository(embedder=mock_embedder)
        repo._mock_collection = mock_collection
    return repo, mock_embedder


def test_is_near_duplicate_returns_true_for_high_similarity():
    repo, _ = make_repo()
    repo._mock_collection.count.return_value = 10
    repo._mock_collection.query.return_value = {
        "ids": [["5"]],
        "distances": [[0.01]],
        "metadatas": [[{"title": "Benzer haber"}]],
    }
    article = make_article(id=None)
    assert repo.is_near_duplicate(article, threshold=0.92) is True


def test_is_near_duplicate_returns_false_for_low_similarity():
    repo, _ = make_repo()
    repo._mock_collection.count.return_value = 10
    repo._mock_collection.query.return_value = {
        "ids": [["5"]],
        "distances": [[2.0]],
        "metadatas": [[{"title": "Farklı haber"}]],
    }
    article = make_article(id=None)
    assert repo.is_near_duplicate(article, threshold=0.92) is False


def test_is_near_duplicate_returns_false_when_collection_empty():
    repo, _ = make_repo()
    repo._mock_collection.count.return_value = 0
    article = make_article(id=None)
    assert repo.is_near_duplicate(article) is False
    repo._mock_collection.query.assert_not_called()


def test_is_near_duplicate_returns_false_on_error():
    repo, _ = make_repo()
    repo._mock_collection.count.return_value = 10
    repo._mock_collection.query.side_effect = Exception("ChromaDB down")
    article = make_article(id=None)
    assert repo.is_near_duplicate(article) is False


def test_is_near_duplicate_returns_false_when_no_results():
    repo, _ = make_repo()
    repo._mock_collection.count.return_value = 10
    repo._mock_collection.query.return_value = {
        "ids": [[]],
        "distances": [[]],
        "metadatas": [[]],
    }
    article = make_article(id=None)
    assert repo.is_near_duplicate(article) is False


def test_is_near_duplicate_uses_title_and_summary():
    repo, embedder = make_repo()
    repo._mock_collection.count.return_value = 10
    repo._mock_collection.query.return_value = {
        "ids": [["1"]],
        "distances": [[1.0]],
        "metadatas": [[]],
    }
    article = make_article(title="Başlık", summary="Özet metni", id=None)
    repo.is_near_duplicate(article)
    call_text = embedder.embed_text.call_args[0][0]
    assert "Başlık" in call_text
    assert "Özet metni" in call_text


def test_is_near_duplicate_threshold_boundary():
    repo, _ = make_repo()
    repo._mock_collection.count.return_value = 10
    # distance 0.05 → similarity = 1/(1+0.05) = 0.9524 → above 0.92
    repo._mock_collection.query.return_value = {
        "ids": [["1"]],
        "distances": [[0.05]],
        "metadatas": [[]],
    }
    article = make_article(id=None)
    assert repo.is_near_duplicate(article, threshold=0.92) is True


def test_index_article_stores_topic_in_metadata():
    repo, _ = make_repo()
    article = make_article(topic="Technology")
    repo.index_article(article)
    call_kwargs = repo._mock_collection.upsert.call_args[1]
    assert call_kwargs["metadatas"][0]["topic"] == "Technology"


def test_index_article_topic_empty_string_when_none():
    repo, _ = make_repo()
    article = make_article(topic=None)
    repo.index_article(article)
    call_kwargs = repo._mock_collection.upsert.call_args[1]
    assert call_kwargs["metadatas"][0]["topic"] == ""
