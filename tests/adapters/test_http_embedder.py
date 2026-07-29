"""HttpEmbedderAdapter ve build_embedder() testleri — gerçek ağ çağrısı YOK."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.adapters.search.http_embedder import EmbeddingServiceError, HttpEmbedderAdapter


def _response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_embed_text_vektoru_dondurur():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000")
    with patch("httpx.post", return_value=_response({"vector": [0.1, 0.2, 0.3]})) as mock_post:
        assert adapter.embed_text("merhaba") == [0.1, 0.2, 0.3]
    assert mock_post.call_args[0][0] == "http://embedder:8000/embed"
    assert mock_post.call_args[1]["json"] == {"text": "merhaba"}


def test_embed_batch_vektor_listesi_dondurur():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000")
    with patch("httpx.post", return_value=_response({"vectors": [[0.1], [0.2]]})) as mock_post:
        assert adapter.embed_batch(["a", "b"]) == [[0.1], [0.2]]
    assert mock_post.call_args[0][0] == "http://embedder:8000/embed-batch"


def test_base_url_sonundaki_slash_temizlenir():
    """Aksi halde istek "http://embedder:8000//embed" adresine giderdi."""
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000/")
    with patch("httpx.post", return_value=_response({"vector": [0.1]})) as mock_post:
        adapter.embed_text("merhaba")
    assert mock_post.call_args[0][0] == "http://embedder:8000/embed"


def test_servis_erisilemezse_EmbeddingServiceError_firlatir():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000", retries=0)
    with patch("httpx.post", side_effect=httpx.ConnectError("baglanti yok")):
        with pytest.raises(EmbeddingServiceError):
            adapter.embed_text("merhaba")


def test_gecici_hatada_yeniden_dener():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000", retries=1)
    calls = [httpx.ConnectError("gecici"), _response({"vector": [0.5]})]
    with patch("httpx.post", side_effect=calls) as mock_post:
        assert adapter.embed_text("merhaba") == [0.5]
    assert mock_post.call_count == 2


def test_retries_sifir_ise_tek_deneme_yapilir():
    """retries=0 gerçekten TEK deneme demeli.

    `retries or settings.embedder_retries` yazılsaydı 0 falsy olduğu için
    sessizce ayarlardaki değere düşerdi — bu tam da o hatayı kilitler.
    """
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000", retries=0)
    with patch("httpx.post", side_effect=httpx.ConnectError("yok")) as mock_post:
        with pytest.raises(EmbeddingServiceError):
            adapter.embed_text("merhaba")
    assert mock_post.call_count == 1


def test_batch_daha_uzun_read_timeout_kullanir():
    """Toplu indeksleme tek cümleden çok daha uzun sürer."""
    adapter = HttpEmbedderAdapter(
        base_url="http://embedder:8000", read_timeout=5.0, batch_read_timeout=30.0
    )
    with patch("httpx.post", return_value=_response({"vectors": [[0.1]]})) as mock_post:
        adapter.embed_batch(["a"])
    assert mock_post.call_args[1]["timeout"].read == 30.0


def test_build_embedder_http_modunda_http_adapter_dondurur():
    from src.adapters.search.embedder_factory import build_embedder
    with patch("src.adapters.search.embedder_factory.settings") as ms:
        ms.embedder_mode = "http"
        assert isinstance(build_embedder(), HttpEmbedderAdapter)


def test_build_embedder_local_modunda_sentence_transformer_dondurur():
    """local mod importu FONKSIYON ICINDE olmali — app/worker image'larinda
    sentence-transformers KURULU DEGIL, modul seviyesinde import edilirse
    o image'lar acilista coker."""
    from src.adapters.search import embedder_factory
    fake = MagicMock()
    with patch("src.adapters.search.embedder_factory.settings") as ms:
        ms.embedder_mode = "local"
        with patch.dict(
            "sys.modules",
            {"src.adapters.search.sentence_transformer_embedder": MagicMock(
                SentenceTransformerEmbedder=MagicMock(return_value=fake))},
        ):
            assert embedder_factory.build_embedder() is fake


def test_embedder_factory_modul_seviyesinde_sentence_transformers_import_etmiyor():
    """Kaynak denetimi: import fonksiyon içinde kalmalı.

    Modül seviyesine taşınırsa app/worker container'ları açılışta ImportError
    ile çöker ve bunu ancak gerçek deploy'da fark ederiz.
    """
    import inspect
    from src.adapters.search import embedder_factory
    source = inspect.getsource(embedder_factory)
    module_level = [
        line for line in source.splitlines()
        if line.startswith("from ") or line.startswith("import ")
    ]
    assert not any("sentence_transformer" in line for line in module_level)
