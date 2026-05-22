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
        content="Bu bir test içeriğidir.",
        summary="Kısa özet.",
        sentiment_label="Neutral",
        sentiment_score=0.0,
    )
    defaults.update(kwargs)
    return Article(**defaults)


def make_repo():
    """Mock embedder ve mock ChromaDB client ile repo oluşturur."""
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 384

    with patch("src.adapters.search.chroma_search_repository.chromadb.HttpClient") as mock_client_cls:
        mock_collection = MagicMock()
        mock_client_cls.return_value.get_or_create_collection.return_value = mock_collection
        repo = ChromaSearchRepository(embedder=mock_embedder)
        repo._mock_collection = mock_collection
    return repo, mock_embedder


# ── index_article ─────────────────────────────────────────────────────────────

def test_index_article_success():
    repo, embedder = make_repo()
    article = make_article()
    result = repo.index_article(article)
    assert result is True
    repo._mock_collection.upsert.assert_called_once()
    call_kwargs = repo._mock_collection.upsert.call_args[1]
    assert call_kwargs["ids"] == ["1"]
    assert call_kwargs["metadatas"][0]["title"] == "Test Haberi"


def test_index_article_no_id_returns_false():
    repo, _ = make_repo()
    article = make_article(id=None)
    result = repo.index_article(article)
    assert result is False
    repo._mock_collection.upsert.assert_not_called()


def test_index_article_chroma_error_returns_false():
    repo, _ = make_repo()
    repo._mock_collection.upsert.side_effect = Exception("ChromaDB bağlantı hatası")
    article = make_article()
    result = repo.index_article(article)
    assert result is False


def test_index_article_uses_summary_in_embedding():
    repo, embedder = make_repo()
    article = make_article(title="Başlık", summary="Özet metin")
    repo.index_article(article)
    call_args = embedder.embed_text.call_args[0][0]
    assert "Başlık" in call_args
    assert "Özet metin" in call_args


def test_index_article_falls_back_to_content_when_no_summary():
    repo, embedder = make_repo()
    article = make_article(summary=None, content="İçerik metni buradadır")
    repo.index_article(article)
    call_args = embedder.embed_text.call_args[0][0]
    assert "İçerik metni" in call_args


# ── search ────────────────────────────────────────────────────────────────────

def test_search_returns_results():
    repo, embedder = make_repo()
    repo._mock_collection.query.return_value = {
        "ids": [["1", "2"]],
        "metadatas": [[
            {"title": "Haber 1", "source": "BBC", "url": "http://a.com", "summary": "Özet 1", "sentiment_label": "Positive"},
            {"title": "Haber 2", "source": "TRT", "url": "http://b.com", "summary": "Özet 2", "sentiment_label": "Neutral"},
        ]],
        "distances": [[0.1, 0.3]],
    }
    results = repo.search("yapay zeka", n_results=2)
    assert len(results) == 2
    assert results[0]["id"] == "1"
    assert results[0]["score"] == round(1 / (1 + 0.1), 4)
    assert results[1]["source"] == "TRT"


def test_search_passes_n_results_to_query():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]]}
    repo.search("sorgu", n_results=5)
    call_kwargs = repo._mock_collection.query.call_args[1]
    assert call_kwargs["n_results"] == 5


def test_search_chroma_error_returns_empty_list():
    repo, _ = make_repo()
    repo._mock_collection.query.side_effect = Exception("Bağlantı kesildi")
    results = repo.search("sorgu")
    assert results == []


def test_search_score_calculation():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {
        "ids": [["42"]],
        "metadatas": [[{"title": "T", "source": "S", "url": "U", "summary": "Ö", "sentiment_label": "N"}]],
        "distances": [[0.0]],
    }
    results = repo.search("mükemmel eşleşme")
    assert results[0]["score"] == 1.0


# ── filter / where ────────────────────────────────────────────────────────────

def test_search_no_filter_passes_none_where():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]]}
    repo.search("sorgu")
    call_kwargs = repo._mock_collection.query.call_args[1]
    assert call_kwargs["where"] is None


def test_search_source_filter_builds_where():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]]}
    repo.search("sorgu", source="BBC Technology")
    call_kwargs = repo._mock_collection.query.call_args[1]
    assert call_kwargs["where"] == {"source": {"$eq": "BBC Technology"}}


def test_search_sentiment_filter_builds_where():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]]}
    repo.search("sorgu", sentiment="Positive")
    call_kwargs = repo._mock_collection.query.call_args[1]
    assert call_kwargs["where"] == {"sentiment_label": {"$eq": "Positive"}}


def test_search_both_filters_builds_and_where():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]]}
    repo.search("sorgu", source="BBC Technology", sentiment="Positive")
    call_kwargs = repo._mock_collection.query.call_args[1]
    assert call_kwargs["where"] == {
        "$and": [
            {"source": {"$eq": "BBC Technology"}},
            {"sentiment_label": {"$eq": "Positive"}},
        ]
    }
