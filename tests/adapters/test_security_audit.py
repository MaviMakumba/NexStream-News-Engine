"""`record_security_event` yardımcısı — router'ların tek satırla olay yazdığı nokta.

Fail-open: güvenlik günlüğü yazılamıyorsa (tablo yok, DB hatası) istek ASLA
bozulmaz, sadece loglanır — projenin genel "exception yut, logla, fallback"
ilkesi. Gizli bilgi (parola/token/anahtar) bu fonksiyona hiç gelmez;
imzası buna izin vermez.
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.adapters.api.request_context import RequestContextMiddleware
from src.adapters.api.security_audit import record_security_event
from src.domain.models.security_event import EventCategory, EventType


def _app(db):
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.post("/thing")
    def thing(request: Request):
        record_security_event(
            db, request, EventCategory.AUTH, EventType.LOGIN_FAILURE,
            email="Ali@Example.com", user_id=None, detail="wrong password",
        )
        return {"ok": True}

    return app


def test_record_fills_ip_user_agent_request_id_and_path_from_request():
    db = MagicMock()
    with patch("src.adapters.api.security_audit.SecurityEventRepository") as MockRepo:
        c = TestClient(_app(db))
        r = c.post("/thing", headers={
            "X-Real-IP": "78.186.147.254", "X-Request-ID": "abc123", "User-Agent": "TestUA/1.0",
        })
    assert r.status_code == 200
    event = MockRepo.return_value.record.call_args[0][0]
    assert event.category == "auth"
    assert event.event_type == "login_failure"
    assert event.email == "ali@example.com"      # normalize edilir
    assert event.ip == "78.186.147.254"
    assert event.user_agent == "TestUA/1.0"
    assert event.request_id == "abc123"
    assert event.path == "/thing"
    assert event.detail == "wrong password"


def test_record_failure_never_breaks_the_request():
    db = MagicMock()
    with patch("src.adapters.api.security_audit.SecurityEventRepository") as MockRepo:
        MockRepo.return_value.record.side_effect = RuntimeError("relation security_events does not exist")
        c = TestClient(_app(db))
        r = c.post("/thing")
    assert r.status_code == 200
    db.rollback.assert_called_once()
