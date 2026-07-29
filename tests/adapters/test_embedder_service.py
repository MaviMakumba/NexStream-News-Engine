"""Embedder servisi endpoint testleri — gerçek model YÜKLENMEZ, mock'lanır."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    fake_embedder = MagicMock()
    fake_embedder.embed_text.return_value = [0.1, 0.2]
    fake_embedder.embed_batch.return_value = [[0.1, 0.2], [0.3, 0.4]]
    from src.adapters.search import embedder_service
    with patch.object(embedder_service, "_get_embedder", return_value=fake_embedder):
        with TestClient(embedder_service.app) as c:
            yield c, fake_embedder


def test_embed_vektor_dondurur(client):
    c, fake = client
    r = c.post("/embed", json={"text": "merhaba dunya"})
    assert r.status_code == 200
    assert r.json() == {"vector": [0.1, 0.2]}
    fake.embed_text.assert_called_once_with("merhaba dunya")


def test_embed_batch_vektor_listesi_dondurur(client):
    c, fake = client
    r = c.post("/embed-batch", json={"texts": ["a", "b"]})
    assert r.status_code == 200
    assert r.json() == {"vectors": [[0.1, 0.2], [0.3, 0.4]]}
    fake.embed_batch.assert_called_once_with(["a", "b"])


def test_bos_metin_422_dondurur(client):
    c, _ = client
    assert c.post("/embed", json={"text": ""}).status_code == 422


def test_bos_batch_422_dondurur(client):
    c, _ = client
    assert c.post("/embed-batch", json={"texts": []}).status_code == 422


def test_cok_buyuk_batch_422_dondurur(client):
    """Tek istekle sınırsız iş yüklenip servis bloklanamamalı."""
    c, _ = client
    assert c.post("/embed-batch", json={"texts": ["x"] * 500}).status_code == 422


def test_health_model_adini_raporlar(client):
    c, _ = client
    body = c.get("/health").json()
    assert body["status"] == "ok"
    assert body["model"] == "paraphrase-multilingual-MiniLM-L12-v2"


def test_docs_kapali(client):
    """Bu servis yalnızca iç ağdan erişilir; dışarı açılmaz, docs gereksiz."""
    c, _ = client
    assert c.get("/docs").status_code == 404
