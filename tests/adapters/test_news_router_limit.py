"""GET /news/?limit= sınırları (15 Ekim 2026, Sentry PYTHON-FASTAPI-18/1A).

`limit` doğrulamasız SQL `LIMIT`'e gidiyordu: 999999999999999999999 (bigint
taşması) ve -1 Postgres hatası → 500. Artık 422 dönmeli, servise hiç inmemeli.
"""

import pytest
from unittest.mock import MagicMock


def _override(app_client, mock_service):
    from src.dependencies import get_news_service
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


@pytest.mark.parametrize("bad", ["-1", "0", "999999999999999999999", "101", "abc"])
def test_news_limit_out_of_range_is_422(app_client, bad):
    svc = MagicMock()
    _override(app_client, svc)
    try:
        r = app_client.get(f"/news/?limit={bad}")
    finally:
        _clear(app_client)
    assert r.status_code == 422
    svc.list_news.assert_not_called()


def test_news_limit_valid_values_pass(app_client):
    svc = MagicMock()
    svc.list_news.return_value = []
    _override(app_client, svc)
    try:
        r1 = app_client.get("/news/?limit=1")
        r2 = app_client.get("/news/?limit=100")
    finally:
        _clear(app_client)
    assert r1.status_code == 200 and r2.status_code == 200
