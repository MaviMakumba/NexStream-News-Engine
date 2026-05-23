from unittest.mock import MagicMock, patch
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.orm_models import NewsORM


def make_repo():
    mock_db = MagicMock()
    return NewsRepository(db=mock_db), mock_db


def test_bulk_exists_returns_matching_urls():
    repo, mock_db = make_repo()
    row1 = MagicMock(); row1.url = "https://example.com/1"
    row2 = MagicMock(); row2.url = "https://example.com/2"
    mock_db.query.return_value.filter.return_value.all.return_value = [row1, row2]

    result = repo.bulk_exists(["https://example.com/1", "https://example.com/2", "https://example.com/3"])

    assert result == {"https://example.com/1", "https://example.com/2"}


def test_bulk_exists_empty_input_returns_empty_set():
    repo, mock_db = make_repo()
    result = repo.bulk_exists([])
    assert result == set()
    mock_db.query.assert_not_called()


def test_bulk_exists_no_matches_returns_empty_set():
    repo, mock_db = make_repo()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = repo.bulk_exists(["https://example.com/new"])

    assert result == set()


def test_bulk_exists_returns_set_not_list():
    repo, mock_db = make_repo()
    row = MagicMock(); row.url = "https://example.com/1"
    mock_db.query.return_value.filter.return_value.all.return_value = [row]

    result = repo.bulk_exists(["https://example.com/1"])

    assert isinstance(result, set)
