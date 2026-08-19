"""SavedArticleRepository testleri — gerçek in-memory SQLite (bkz. test_news_repository.py deseni)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.config.database import Base
from src.adapters.repositories.saved_article_repository import SavedArticleRepository
from src.adapters.repositories.orm_models import SavedArticleORM


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_save_adds_row():
    db = make_session()
    repo = SavedArticleRepository(db)

    result = repo.save(user_id=1, article_id=42)

    assert result is True
    assert db.query(SavedArticleORM).count() == 1


def test_save_is_idempotent():
    """Aynı haberi iki kez kaydetmek ikinci satır açmamalı."""
    db = make_session()
    repo = SavedArticleRepository(db)

    repo.save(user_id=1, article_id=42)
    result = repo.save(user_id=1, article_id=42)

    assert result is True
    assert db.query(SavedArticleORM).count() == 1


def test_unsave_removes_row():
    db = make_session()
    repo = SavedArticleRepository(db)
    repo.save(user_id=1, article_id=42)

    result = repo.unsave(user_id=1, article_id=42)

    assert result is True
    assert db.query(SavedArticleORM).count() == 0


def test_unsave_returns_false_when_not_saved():
    db = make_session()
    repo = SavedArticleRepository(db)

    assert repo.unsave(user_id=1, article_id=42) is False


def test_is_saved_reflects_state():
    db = make_session()
    repo = SavedArticleRepository(db)

    assert repo.is_saved(user_id=1, article_id=42) is False
    repo.save(user_id=1, article_id=42)
    assert repo.is_saved(user_id=1, article_id=42) is True


def test_list_saved_article_ids_most_recent_first():
    db = make_session()
    repo = SavedArticleRepository(db)

    repo.save(user_id=1, article_id=1)
    repo.save(user_id=1, article_id=2)
    repo.save(user_id=1, article_id=3)

    assert repo.list_saved_article_ids(user_id=1) == [3, 2, 1]


def test_list_saved_article_ids_scoped_to_user():
    db = make_session()
    repo = SavedArticleRepository(db)
    repo.save(user_id=1, article_id=99)
    repo.save(user_id=2, article_id=100)

    assert repo.list_saved_article_ids(user_id=1) == [99]


def test_delete_for_user_removes_all_rows():
    db = make_session()
    repo = SavedArticleRepository(db)
    repo.save(user_id=1, article_id=1)
    repo.save(user_id=1, article_id=2)
    repo.save(user_id=2, article_id=3)

    repo.delete_for_user(1)

    assert repo.list_saved_article_ids(user_id=1) == []
    assert repo.list_saved_article_ids(user_id=2) == [3]
