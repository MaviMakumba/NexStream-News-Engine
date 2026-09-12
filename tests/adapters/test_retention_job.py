import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.infrastructure.config.settings import settings
from src.domain.models.article import Article


def _article(id_=1):
    a = Article(title="Eski Haber", source="TRT", url=f"http://t.com/{id_}", content="içerik")
    a.id = id_
    return a


@pytest.mark.asyncio
async def test_retention_job_chroma_delete_called_when_enabled():
    from src.adapters.scheduling.retention_job import _run_retention

    mock_search = MagicMock()
    mock_search.delete_before.return_value = 5
    mock_search.index_article.return_value = True

    with patch.object(settings, "chroma_retention_days", 90), \
         patch.object(settings, "db_retention_days", 0), \
         patch("src.adapters.scheduling.retention_job.get_search_repository", return_value=mock_search), \
         patch("src.adapters.scheduling.retention_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.retention_job.NewsRepository") as MockNewsRepo:
        MockSession.return_value = MagicMock()
        news_repo = MagicMock()
        news_repo.get_articles_created_after.return_value = []
        MockNewsRepo.return_value = news_repo

        await _run_retention()

    mock_search.delete_before.assert_called_once()
    news_repo.delete_articles_before.assert_not_called()


@pytest.mark.asyncio
async def test_retention_job_chroma_delete_skipped_when_disabled():
    from src.adapters.scheduling.retention_job import _run_retention

    mock_search = MagicMock()
    mock_search.index_article.return_value = True

    with patch.object(settings, "chroma_retention_days", 0), \
         patch.object(settings, "db_retention_days", 0), \
         patch("src.adapters.scheduling.retention_job.get_search_repository", return_value=mock_search), \
         patch("src.adapters.scheduling.retention_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.retention_job.NewsRepository") as MockNewsRepo:
        MockSession.return_value = MagicMock()
        news_repo = MagicMock()
        news_repo.get_articles_created_after.return_value = []
        MockNewsRepo.return_value = news_repo

        await _run_retention()

    mock_search.delete_before.assert_not_called()


@pytest.mark.asyncio
async def test_retention_job_db_delete_skipped_by_default():
    """db_retention_days varsayılan 0 (kapalı) — kalıcı silme tetiklenmemeli."""
    from src.adapters.scheduling.retention_job import _run_retention

    mock_search = MagicMock()
    mock_search.index_article.return_value = True

    with patch.object(settings, "chroma_retention_days", 0), \
         patch.object(settings, "db_retention_days", 0), \
         patch("src.adapters.scheduling.retention_job.get_search_repository", return_value=mock_search), \
         patch("src.adapters.scheduling.retention_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.retention_job.NewsRepository") as MockNewsRepo:
        MockSession.return_value = MagicMock()
        news_repo = MagicMock()
        news_repo.get_articles_created_after.return_value = []
        MockNewsRepo.return_value = news_repo

        await _run_retention()

    news_repo.delete_articles_before.assert_not_called()


@pytest.mark.asyncio
async def test_retention_job_db_delete_called_when_explicitly_enabled():
    from src.adapters.scheduling.retention_job import _run_retention

    mock_search = MagicMock()
    mock_search.index_article.return_value = True

    with patch.object(settings, "chroma_retention_days", 0), \
         patch.object(settings, "db_retention_days", 365), \
         patch("src.adapters.scheduling.retention_job.get_search_repository", return_value=mock_search), \
         patch("src.adapters.scheduling.retention_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.retention_job.NewsRepository") as MockNewsRepo:
        MockSession.return_value = MagicMock()
        news_repo = MagicMock()
        news_repo.delete_articles_before.return_value = 2
        news_repo.get_articles_created_after.return_value = []
        MockNewsRepo.return_value = news_repo

        await _run_retention()

    news_repo.delete_articles_before.assert_called_once()


@pytest.mark.asyncio
async def test_retention_job_self_heals_recent_unindexed_articles():
    from src.adapters.scheduling.retention_job import _run_retention

    mock_search = MagicMock()
    mock_search.index_article.return_value = True
    recent_articles = [_article(1), _article(2)]

    with patch.object(settings, "chroma_retention_days", 0), \
         patch.object(settings, "db_retention_days", 0), \
         patch("src.adapters.scheduling.retention_job.get_search_repository", return_value=mock_search), \
         patch("src.adapters.scheduling.retention_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.retention_job.NewsRepository") as MockNewsRepo:
        MockSession.return_value = MagicMock()
        news_repo = MagicMock()
        news_repo.get_articles_created_after.return_value = recent_articles
        MockNewsRepo.return_value = news_repo

        await _run_retention()

    assert mock_search.index_article.call_count == 2


@pytest.mark.asyncio
async def test_retention_job_purges_security_events_older_than_configured_days():
    """security_events kişisel veri içerir (IP/e-posta/UA) — sonsuz log YOK,
    varsayılan 90 gün (13 Eyl 2026)."""
    from src.adapters.scheduling.retention_job import _run_retention

    mock_search = MagicMock()
    with patch.object(settings, "chroma_retention_days", 0), \
         patch.object(settings, "db_retention_days", 0), \
         patch.object(settings, "security_events_retention_days", 90), \
         patch("src.adapters.scheduling.retention_job.get_search_repository", return_value=mock_search), \
         patch("src.adapters.scheduling.retention_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.retention_job.NewsRepository") as MockNewsRepo, \
         patch("src.adapters.scheduling.retention_job.SecurityEventRepository") as MockSecRepo:
        MockSession.return_value = MagicMock()
        MockNewsRepo.return_value.get_articles_created_after.return_value = []
        MockSecRepo.return_value.delete_older_than.return_value = 3

        await _run_retention()

    cutoff = MockSecRepo.return_value.delete_older_than.call_args[0][0]
    assert 89 <= (datetime.now(timezone.utc) - cutoff).days <= 90
