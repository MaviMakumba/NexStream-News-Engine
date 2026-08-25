"""PushSubscriptionRepository testleri — gerçek in-memory SQLite (bkz. test_saved_article_repository.py deseni)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.config.database import Base
from src.domain.models.push_subscription import PushSubscription
from src.adapters.repositories.push_subscription_repository import PushSubscriptionRepository
from src.adapters.repositories.orm_models import PushSubscriptionORM


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _sub(email="me@test.com", endpoint="https://push.example.com/abc"):
    return PushSubscription(email=email, endpoint=endpoint, p256dh="p256dh-key", auth="auth-secret")


def test_save_adds_row():
    db = make_session()
    repo = PushSubscriptionRepository(db)

    result = repo.save(_sub())

    assert result.id is not None
    assert db.query(PushSubscriptionORM).count() == 1


def test_save_same_endpoint_upserts_not_duplicates():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub())

    result = repo.save(_sub(endpoint="https://push.example.com/abc"))

    assert db.query(PushSubscriptionORM).count() == 1
    assert result.endpoint == "https://push.example.com/abc"


def test_get_by_email_returns_all_devices():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub(endpoint="https://push.example.com/device1"))
    repo.save(_sub(endpoint="https://push.example.com/device2"))
    repo.save(_sub(email="other@test.com", endpoint="https://push.example.com/device3"))

    result = repo.get_by_email("me@test.com")

    assert len(result) == 2
    assert {s.endpoint for s in result} == {
        "https://push.example.com/device1", "https://push.example.com/device2",
    }


def test_get_by_email_returns_empty_list_when_none():
    db = make_session()
    repo = PushSubscriptionRepository(db)

    assert repo.get_by_email("nobody@test.com") == []


def test_delete_by_endpoint_removes_row():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub())

    result = repo.delete_by_endpoint("https://push.example.com/abc")

    assert result is True
    assert db.query(PushSubscriptionORM).count() == 0


def test_delete_by_endpoint_returns_false_when_not_found():
    db = make_session()
    repo = PushSubscriptionRepository(db)

    assert repo.delete_by_endpoint("https://push.example.com/missing") is False


def test_delete_by_email_removes_all_devices_for_that_email_only():
    db = make_session()
    repo = PushSubscriptionRepository(db)
    repo.save(_sub(endpoint="https://push.example.com/device1"))
    repo.save(_sub(endpoint="https://push.example.com/device2"))
    repo.save(_sub(email="other@test.com", endpoint="https://push.example.com/device3"))

    repo.delete_by_email("me@test.com")

    assert repo.get_by_email("me@test.com") == []
    assert len(repo.get_by_email("other@test.com")) == 1
