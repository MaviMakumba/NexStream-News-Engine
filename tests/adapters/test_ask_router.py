from unittest.mock import MagicMock

from src.domain.models.user import User, UserTier
from src.adapters.api.auth_utils import check_tier_limit
from src.domain.ports.question_answering_port import QuestionAnsweringError


def _override(app_client, mock_service):
    from src.dependencies import get_news_service
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service


def _override_pro(app_client, mock_service):
    _override(app_client, mock_service)
    pro = User(id=1, email="pro@test.com", password_hash="h", tier=UserTier.PRO)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: pro


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


_PAYLOAD = {
    "answer": "Cevap burada.",
    "coverage": "full",
    "corroboration_level": "multi_source",
    "sources": [{"index": 1, "title": "Başlık", "source": "BBC", "url": "http://x"}],
    "suggest_alert": False,
}


def test_ask_endpoint_returns_payload_for_pro_user(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.return_value = _PAYLOAD
    _override_pro(app_client, mock_service)
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)

    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == "Cevap burada."
    assert data["coverage"] == "full"
    assert data["sources"][0]["source"] == "BBC"


def test_ask_endpoint_blocked_for_free_tier(app_client):
    mock_service = MagicMock()
    _override(app_client, mock_service)
    free = User(id=1, email="free@test.com", password_hash="h", tier=UserTier.FREE)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: free
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)
    assert r.status_code == 403
    mock_service.answer_question.assert_not_called()


def test_ask_endpoint_blocked_for_anonymous(app_client):
    mock_service = MagicMock()
    _override(app_client, mock_service)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: None
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)
    assert r.status_code == 403


def test_ask_endpoint_404_when_article_not_found(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.return_value = None
    _override_pro(app_client, mock_service)
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?", "article_id": 999})
    finally:
        _clear(app_client)
    assert r.status_code == 404


def test_ask_endpoint_503_on_question_answering_error(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.side_effect = QuestionAnsweringError("Groq: tüm denemeler başarısız")
    _override_pro(app_client, mock_service)
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)
    assert r.status_code == 503


def test_ask_endpoint_passes_article_id_and_history(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.return_value = _PAYLOAD
    _override_pro(app_client, mock_service)
    try:
        app_client.post("/api/v1/news/ask", json={
            "question": "Peki ya İzmir'de?",
            "article_id": 42,
            "history": [{"role": "user", "content": "İstanbul'da ne oldu?"},
                        {"role": "assistant", "content": "..."}],
        })
    finally:
        _clear(app_client)

    mock_service.answer_question.assert_called_once_with(
        "Peki ya İzmir'de?",
        article_id=42,
        history=[{"role": "user", "content": "İstanbul'da ne oldu?"},
                 {"role": "assistant", "content": "..."}],
    )


def test_ask_endpoint_rejects_empty_question(app_client):
    r = app_client.post("/api/v1/news/ask", json={"question": ""})
    assert r.status_code == 422


def test_ask_endpoint_not_registered_on_legacy_router(app_client):
    """Bilinçli tasarım kararı (26 Ağu 2026): endpoint SADECE /api/v1'de,
    kota sayacına (usage_tracking_middleware) dahil olsun diye."""
    r = app_client.post("/news/ask", json={"question": "Ne oldu?"})
    assert r.status_code == 404
