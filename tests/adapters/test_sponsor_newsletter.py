import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from src.adapters.notifications.email_adapter import _digest_html, ConsoleEmailAdapter
from src.domain.models.article import Article
from src.domain.models.sponsor import Sponsor


def _article(title="Test Haberi"):
    a = Article(title=title, source="TRT", url="http://t.com", content="içerik")
    a.summary = "Özet"
    a.sentiment_label = "Positive"
    a.topic = "Tech"
    a.id = 1
    return a


def _sponsor():
    now = datetime.now(timezone.utc)
    return Sponsor(
        id=1,
        name="Acme Corp",
        url="https://acme.example.com",
        message="The best product for developers",
        active_from=now - timedelta(days=1),
        active_until=now + timedelta(days=30),
        is_active=True,
    )


# ── _digest_html ──────────────────────────────────────────────────────────────

def test_digest_html_without_sponsor_has_no_sponsor_block():
    html = _digest_html([_article()], "TR", sponsor=None)
    assert "Acme Corp" not in html
    assert "sponsor" not in html.lower() or "unsubscribe" in html  # footer only


def test_digest_html_with_sponsor_includes_sponsor_name():
    html = _digest_html([_article()], "TR", sponsor=_sponsor())
    assert "Acme Corp" in html


def test_digest_html_with_sponsor_includes_sponsor_url():
    html = _digest_html([_article()], "EN", sponsor=_sponsor())
    assert "https://acme.example.com" in html


def test_digest_html_with_sponsor_includes_message():
    html = _digest_html([_article()], "TR", sponsor=_sponsor())
    assert "The best product for developers" in html


def test_console_adapter_logs_sponsor_name():
    import logging
    adapter = ConsoleEmailAdapter()
    with patch.object(logging.getLogger("src.adapters.notifications.email_adapter"), "info") as mock_log:
        adapter.send_digest("user@test.com", [_article()], "TR", sponsor=_sponsor())
    mock_log.assert_called_once()
    call_args = mock_log.call_args[0]
    assert "Acme Corp" in str(call_args)


def test_console_adapter_handles_no_sponsor():
    adapter = ConsoleEmailAdapter()
    result = adapter.send_digest("user@test.com", [_article()], "TR", sponsor=None)
    assert result is True


# ── newsletter_job with sponsor ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_newsletter_job_includes_active_sponsor():
    from src.adapters.scheduling.newsletter_job import _send_digests

    mock_email = MagicMock()
    mock_email.send_digest.return_value = True

    mock_article = _article()
    active_sponsor = _sponsor()

    with patch("src.adapters.scheduling.newsletter_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.newsletter_job.NewsRepository") as MockNewsRepo, \
         patch("src.adapters.scheduling.newsletter_job.SubscriberRepository") as MockSubRepo, \
         patch("src.adapters.scheduling.newsletter_job.get_active_sponsor", return_value=active_sponsor):

        db = MagicMock()
        MockSession.return_value.__enter__ = MagicMock(return_value=db)
        MockSession.return_value.__exit__ = MagicMock(return_value=None)
        MockSession.return_value = db

        news_repo = MagicMock()
        news_repo.get_latest_news.return_value = [mock_article]
        MockNewsRepo.return_value = news_repo

        from src.domain.models.subscriber import Subscriber
        sub = Subscriber(email="sub@test.com", frequency="daily", language="TR")
        sub_repo = MagicMock()
        sub_repo.get_active_subscribers.return_value = [sub]
        MockSubRepo.return_value = sub_repo

        await _send_digests(mock_email)

    mock_email.send_digest.assert_called_once()
    call_kwargs = mock_email.send_digest.call_args[1]
    assert call_kwargs["sponsor"] is active_sponsor


@pytest.mark.asyncio
async def test_newsletter_job_works_without_sponsor():
    from src.adapters.scheduling.newsletter_job import _send_digests

    mock_email = MagicMock()
    mock_email.send_digest.return_value = True

    with patch("src.adapters.scheduling.newsletter_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.newsletter_job.NewsRepository") as MockNewsRepo, \
         patch("src.adapters.scheduling.newsletter_job.SubscriberRepository") as MockSubRepo, \
         patch("src.adapters.scheduling.newsletter_job.get_active_sponsor", return_value=None):

        db = MagicMock()
        MockSession.return_value = db

        news_repo = MagicMock()
        news_repo.get_latest_news.return_value = [_article()]
        MockNewsRepo.return_value = news_repo

        from src.domain.models.subscriber import Subscriber
        sub = Subscriber(email="sub@test.com", frequency="daily", language="EN")
        sub_repo = MagicMock()
        sub_repo.get_active_subscribers.return_value = [sub]
        MockSubRepo.return_value = sub_repo

        await _send_digests(mock_email)

    mock_email.send_digest.assert_called_once()
    call_kwargs = mock_email.send_digest.call_args[1]
    assert call_kwargs["sponsor"] is None
