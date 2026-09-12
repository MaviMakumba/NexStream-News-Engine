"""security_events güvenlik günlüğü — repository testleri (13 Eylül 2026).

12 Eylül olayında DB'de `created_at` vardı, nginx logunda IP vardı ama ikisi
kalıcı olarak bağlı değildi; "bu hesabı kim açtı?" sorusu saniye eşleştirerek
cevaplandı. Bu tablo olayı, IP'yi, user-agent'ı ve nginx'in `request_id`'sini
tek satırda tutar. Kişisel veri içerdiği için 90 gün sonra silinir.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.database import Base
from src.domain.models.security_event import SecurityEvent, EventCategory, EventType
from src.adapters.repositories.security_event_repository import SecurityEventRepository


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _event(**overrides):
    base = dict(
        category=EventCategory.AUTH, event_type=EventType.LOGIN_FAILURE,
        email="ali@example.com", user_id=None, ip="78.186.147.254",
        user_agent="Mozilla/5.0", request_id="abc123", path="/auth/login", detail=None,
    )
    base.update(overrides)
    return SecurityEvent(**base)


def test_record_persists_all_fields_and_returns_id():
    db = _session()
    repo = SecurityEventRepository(db)
    saved = repo.record(_event(detail="wrong password"))
    assert saved.id is not None
    rows = repo.query(limit=10)
    assert len(rows) == 1
    r = rows[0]
    assert (r.category, r.event_type, r.email, r.ip, r.user_agent, r.request_id, r.path, r.detail) == (
        "auth", "login_failure", "ali@example.com", "78.186.147.254", "Mozilla/5.0", "abc123", "/auth/login", "wrong password"
    )
    assert r.created_at is not None


def test_record_truncates_long_user_agent_and_detail():
    db = _session()
    repo = SecurityEventRepository(db)
    repo.record(_event(user_agent="U" * 1000, detail="D" * 1000))
    r = repo.query(limit=1)[0]
    assert len(r.user_agent) == 256
    assert len(r.detail) == 500


def test_query_filters_by_email_ip_and_event_type():
    db = _session()
    repo = SecurityEventRepository(db)
    repo.record(_event(email="a@x.com", ip="1.1.1.1", event_type=EventType.REGISTER))
    repo.record(_event(email="b@x.com", ip="2.2.2.2", event_type=EventType.LOGIN_SUCCESS))
    repo.record(_event(email="a@x.com", ip="2.2.2.2", event_type=EventType.LOGIN_FAILURE))
    assert {r.ip for r in repo.query(email="a@x.com")} == {"1.1.1.1", "2.2.2.2"}
    assert {r.email for r in repo.query(ip="2.2.2.2")} == {"a@x.com", "b@x.com"}
    assert [r.email for r in repo.query(event_type="register")] == ["a@x.com"]
    assert repo.query(email="A@X.COM", ip="1.1.1.1")[0].event_type == "register"


def test_query_filters_by_since_and_orders_newest_first():
    db = _session()
    repo = SecurityEventRepository(db)
    old = repo.record(_event(email="old@x.com"))
    repo._set_created_at(old.id, datetime.now(timezone.utc) - timedelta(days=5))
    repo.record(_event(email="new@x.com"))
    since = datetime.now(timezone.utc) - timedelta(days=1)
    rows = repo.query(since=since)
    assert [r.email for r in rows] == ["new@x.com"]
    assert [r.email for r in repo.query()] == ["new@x.com", "old@x.com"]


def test_delete_older_than_removes_only_expired_rows():
    db = _session()
    repo = SecurityEventRepository(db)
    old = repo.record(_event(email="old@x.com"))
    repo._set_created_at(old.id, datetime.now(timezone.utc) - timedelta(days=100))
    repo.record(_event(email="new@x.com"))
    removed = repo.delete_older_than(datetime.now(timezone.utc) - timedelta(days=90))
    assert removed == 1
    assert [r.email for r in repo.query()] == ["new@x.com"]
