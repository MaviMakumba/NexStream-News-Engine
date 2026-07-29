import pytest
from datetime import datetime, timezone
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


# ── embedder kompozisyonu ─────────────────────────────────────────────────────

def test_varsayilan_embedder_factory_uzerinden_kurulur():
    """Varsayılan embedder build_embedder()'dan gelmeli.

    SentenceTransformerEmbedder DOĞRUDAN kurulursa app/worker image'larında
    (sentence-transformers kurulu DEĞİL) çalışma anında çöker.
    """
    fake_embedder = MagicMock()
    with patch("src.adapters.search.chroma_search_repository.build_embedder",
               return_value=fake_embedder) as mock_build:
        with patch("src.adapters.search.chroma_search_repository.chromadb.HttpClient"):
            repo = ChromaSearchRepository()
    mock_build.assert_called_once()
    assert repo.embedder is fake_embedder


def test_modul_sentence_transformers_import_etmiyor():
    """chroma_search_repository, sentence_transformers'ı modül seviyesinde
    import ETMEMELİ — app/worker image'larında bu paket bulunmayacak."""
    import inspect
    from src.adapters.search import chroma_search_repository
    source = inspect.getsource(chroma_search_repository)
    assert "from src.adapters.search.sentence_transformer_embedder import" not in source
    assert "import sentence_transformers" not in source


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


def test_index_article_metadata_includes_published_at():
    repo, _ = make_repo()
    published = datetime(2026, 6, 1, tzinfo=timezone.utc)
    article = make_article(published_at=published)
    repo.index_article(article)
    meta = repo._mock_collection.upsert.call_args[1]["metadatas"][0]
    assert meta["published_at"] == published.isoformat()


def test_index_article_metadata_falls_back_to_created_at():
    repo, _ = make_repo()
    created = datetime(2026, 5, 1, tzinfo=timezone.utc)
    article = make_article(published_at=None, created_at=created)
    repo.index_article(article)
    meta = repo._mock_collection.upsert.call_args[1]["metadatas"][0]
    assert meta["published_at"] == created.isoformat()


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


def test_search_returns_published_at_from_metadata():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {
        "ids": [["1"]],
        "metadatas": [[{"title": "T", "source": "S", "url": "U", "summary": "Ö",
                         "sentiment_label": "N", "published_at": "2026-06-01T00:00:00+00:00"}]],
        "distances": [[0.1]],
    }
    results = repo.search("sorgu")
    assert results[0]["published_at"] == "2026-06-01T00:00:00+00:00"


def test_search_missing_published_at_defaults_empty():
    repo, _ = make_repo()
    repo._mock_collection.query.return_value = {
        "ids": [["1"]],
        "metadatas": [[{"title": "T", "source": "S", "url": "U", "summary": "Ö", "sentiment_label": "N"}]],
        "distances": [[0.1]],
    }
    results = repo.search("sorgu")
    assert results[0]["published_at"] == ""


# ── delete_before (retention) ──────────────────────────────────────────────────

def _page(ids, metadatas):
    """collection.get() yanıtı taklidi."""
    return {"ids": ids, "metadatas": metadatas}


def test_delete_before_metadatayi_tarayip_id_ile_siler():
    """`where={"published_at": {"$lt": ...}}` KULLANILAMAZ.

    ChromaDB `$lt` operatörünü yalnızca int/float için kabul eder; ISO tarih
    string'i verilince `ValueError` fırlatır. Eski kod tam olarak bunu yapıyordu
    ve hata `except` bloğunda yutulduğu için retention job'ı her gece sessizce
    0 vektör silmişti. Bu test doğru yolu kilitler: metadata taranır, eskiler
    Python'da seçilir, `delete(ids=...)` ile silinir.
    """
    repo, _ = make_repo()
    repo._mock_collection.get.return_value = _page(
        ["1", "2", "3"],
        [
            {"published_at": "2026-01-01T00:00:00"},   # eski → silinecek
            {"published_at": "2026-07-01T00:00:00"},   # yeni → kalacak
            {"published_at": "2026-02-15T00:00:00"},   # eski → silinecek
        ],
    )
    deleted = repo.delete_before("2026-04-01T00:00:00")

    repo._mock_collection.delete.assert_called_once_with(ids=["1", "3"])
    assert deleted == 2


def test_delete_before_tarihsiz_vektorleri_silmez():
    """`published_at` boşsa vektör KORUNUR.

    Boş string her cutoff'tan küçük sayılırdı ve tarihi bilinmeyen her vektör
    sessizce silinirdi. Bilmediğimiz bir şeyi silmektense tutuyoruz.
    """
    repo, _ = make_repo()
    repo._mock_collection.get.return_value = _page(
        ["1", "2"],
        [{"published_at": ""}, {"source": "TRT"}],
    )
    deleted = repo.delete_before("2026-04-01T00:00:00")

    repo._mock_collection.delete.assert_not_called()
    assert deleted == 0


def test_delete_before_silinecek_yoksa_delete_cagirmaz():
    repo, _ = make_repo()
    repo._mock_collection.get.return_value = _page(
        ["1"], [{"published_at": "2026-07-01T00:00:00"}]
    )
    assert repo.delete_before("2026-04-01T00:00:00") == 0
    repo._mock_collection.delete.assert_not_called()


def test_delete_before_koleksiyonu_sayfalayarak_tarar():
    """Tüm metadata tek seferde RAM'e çekilmez — t3.small'da (1.9GB) bu iş
    bilerek sayfalanır."""
    repo, _ = make_repo()
    batch = ChromaSearchRepository.RETENTION_SCAN_BATCH
    first = _page(
        [str(i) for i in range(batch)],
        [{"published_at": "2026-01-01T00:00:00"}] * batch,
    )
    second = _page(["son"], [{"published_at": "2026-01-02T00:00:00"}])
    repo._mock_collection.get.side_effect = [first, second]

    deleted = repo.delete_before("2026-04-01T00:00:00")

    assert deleted == batch + 1
    assert repo._mock_collection.get.call_count == 2
    assert repo._mock_collection.get.call_args_list[1][1]["offset"] == batch


def test_delete_before_returns_zero_on_error():
    repo, _ = make_repo()
    repo._mock_collection.get.side_effect = Exception("bağlantı hatası")
    deleted = repo.delete_before("2026-04-01T00:00:00+00:00")
    assert deleted == 0


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
