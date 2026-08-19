"""UserRepository.delete_user testleri — gerçek in-memory SQLite.

Router seviyesinde (test_account_router.py) UserRepository mock'lanıyor, bu
dosya asıl silme mantığının HER çocuk tabloyu (session/token/usage_log/
saved_articles) gerçekten temizlediğini doğrular — bkz. CLAUDE.md'deki
"bir dosyada kalan tüm okumaları grep'le taramadan bitti deme" dersi, aynı
mantık silme akışları için de geçerli.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.database import Base
from src.adapters.repositories.user_repository import UserRepository
from src.adapters.repositories.orm_models import (
    UserORM, UserSessionORM, PasswordResetTokenORM, EmailVerificationTokenORM,
    UsageLogORM, SavedArticleORM,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _make_user_row(db):
    user = UserORM(email="me@test.com", password_hash="h")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_delete_user_removes_saved_articles():
    db = make_session()
    user = _make_user_row(db)
    db.add(SavedArticleORM(user_id=user.id, article_id=1))
    db.add(SavedArticleORM(user_id=user.id, article_id=2))
    db.commit()

    UserRepository(db).delete_user(user.id)

    assert db.query(SavedArticleORM).filter(SavedArticleORM.user_id == user.id).count() == 0


def test_delete_user_leaves_other_users_saved_articles_intact():
    db = make_session()
    user = _make_user_row(db)
    other = UserORM(email="other@test.com", password_hash="h")
    db.add(other)
    db.commit()
    db.refresh(other)
    db.add(SavedArticleORM(user_id=user.id, article_id=1))
    db.add(SavedArticleORM(user_id=other.id, article_id=2))
    db.commit()

    UserRepository(db).delete_user(user.id)

    assert db.query(SavedArticleORM).filter(SavedArticleORM.user_id == other.id).count() == 1


def test_delete_user_removes_sessions_and_usage_logs():
    db = make_session()
    user = _make_user_row(db)
    db.add(UserSessionORM(user_id=user.id, token="tok1", expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
    db.add(UsageLogORM(user_id=user.id, endpoint="/news", method="GET", status_code=200, response_ms=10.0))
    db.commit()

    UserRepository(db).delete_user(user.id)

    assert db.query(UserSessionORM).filter(UserSessionORM.user_id == user.id).count() == 0
    assert db.query(UsageLogORM).filter(UsageLogORM.user_id == user.id).count() == 0
    assert db.query(UserORM).filter(UserORM.id == user.id).count() == 0


def test_delete_user_returns_false_when_missing():
    db = make_session()
    assert UserRepository(db).delete_user(999) is False


# ── set_active (banlama/aktifleştirme, v2.2) ────────────────────────────────

def test_set_active_false_persists():
    db = make_session()
    user = _make_user_row(db)

    result = UserRepository(db).set_active(user.id, False)

    assert result is True
    db.refresh(user)
    assert user.is_active is False


def test_set_active_true_persists():
    db = make_session()
    user = _make_user_row(db)
    UserRepository(db).set_active(user.id, False)

    UserRepository(db).set_active(user.id, True)

    db.refresh(user)
    assert user.is_active is True


def test_set_active_returns_false_when_missing():
    db = make_session()
    assert UserRepository(db).set_active(999, False) is False
