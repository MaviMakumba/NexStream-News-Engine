import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from src.adapters.notifications.email_adapter import _digest_html, ConsoleEmailAdapter
from src.domain.models.article import Article
from src.domain.models.sponsor import Sponsor


def _article(title="Test Haberi", topic="Tech", source="TRT"):
    a = Article(title=title, source=source, url="http://t.com/" + title, content="içerik " + title)
    a.summary = "Özet"
    a.sentiment_label = "Positive"
    a.topic = topic
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
    html = _digest_html("user@test.com", [_article()], "TR", sponsor=None)
    assert "Acme Corp" not in html
    assert "sponsor" not in html.lower() or "unsubscribe" in html  # footer only


def test_digest_html_with_sponsor_includes_sponsor_name():
    html = _digest_html("user@test.com", [_article()], "TR", sponsor=_sponsor())
    assert "Acme Corp" in html


def test_digest_html_with_sponsor_includes_sponsor_url():
    html = _digest_html("user@test.com", [_article()], "EN", sponsor=_sponsor())
    assert "https://acme.example.com" in html


def test_digest_html_with_sponsor_includes_message():
    html = _digest_html("user@test.com", [_article()], "TR", sponsor=_sponsor())
    assert "The best product for developers" in html


# ── Gerçek kullanıcı bulgularının regresyon testleri ──────────────────────────

def test_digest_html_translates_topic_for_tr_language():
    """Konu etiketleri TR abonede çevrilmeli — önceden ham İngilizce basılıyordu."""
    a = _article()
    a.topic = "Sports"
    html = _digest_html("user@test.com", [a], "TR", sponsor=None)
    assert "Spor" in html
    assert ">Sports<" not in html and "· Sports" not in html


def test_digest_html_keeps_topic_in_english_for_en_language():
    a = _article()
    a.topic = "Sports"
    html = _digest_html("user@test.com", [a], "EN", sponsor=None)
    assert "Sports" in html


def test_sponsor_label_respects_language_not_hardcoded_true():
    """Eskiden `if True else` yüzünden dil ne olursa olsun hep Türkçe basılıyordu."""
    html_en = _digest_html("user@test.com", [_article()], "EN", sponsor=_sponsor())
    assert "This week's sponsor" in html_en
    assert "Bu haftanın sponsoru" not in html_en

    html_tr = _digest_html("user@test.com", [_article()], "TR", sponsor=_sponsor())
    assert "Bu haftanın sponsoru" in html_tr


def test_digest_html_unsubscribe_link_is_real_not_placeholder():
    """Eskiden link hedefi hiç doldurulmayan '{unsubscribe_url}' placeholder'ıydı."""
    html = _digest_html("user@test.com", [_article()], "TR", sponsor=None)
    assert "{unsubscribe_url}" not in html
    assert "/subscriptions/unsubscribe?email=user%40test.com" in html


def test_digest_html_unsubscribe_label_translated_for_en():
    html = _digest_html("user@test.com", [_article()], "EN", sponsor=None)
    assert "Unsubscribe" in html


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


# ── Digest kişiselleştirmesi ───────────────────────────────────────────────────

def test_personalize_returns_general_pool_when_no_preferences():
    from src.adapters.scheduling.newsletter_job import _personalize
    from src.domain.models.subscriber import Subscriber

    pool = [_article("A", topic="Sports"), _article("B", topic="Politics")]
    sub = Subscriber(email="x@test.com")  # tercih yok
    assert _personalize(pool, sub) == pool


def test_personalize_filters_by_preferred_topic():
    from src.adapters.scheduling.newsletter_job import _personalize
    from src.domain.models.subscriber import Subscriber

    sports = _article("Maç", topic="Sports")
    politics = _article("Seçim", topic="Politics")
    sub = Subscriber(email="x@test.com", preferred_topics=["Sports"])
    result = _personalize([sports, politics], sub)
    assert result == [sports]


def test_personalize_falls_back_to_general_pool_when_no_match():
    """Tercih var ama havuzda eşleşen haber yoksa genel havuza düş — boş mail atma."""
    from src.adapters.scheduling.newsletter_job import _personalize
    from src.domain.models.subscriber import Subscriber

    pool = [_article("A", topic="Sports"), _article("B", topic="Sports")]
    sub = Subscriber(email="x@test.com", preferred_topics=["Politics"])
    assert _personalize(pool, sub) == pool


def test_personalize_respects_limit():
    from src.adapters.scheduling.newsletter_job import _personalize
    from src.domain.models.subscriber import Subscriber

    pool = [_article(f"H{i}", topic="Sports") for i in range(5)]
    sub = Subscriber(email="x@test.com", preferred_topics=["Sports"])
    assert len(_personalize(pool, sub, limit=2)) == 2


# ── Çoklu-worker duplicate önleme (20 Ağu 2026'da canlıda bulundu) ────────────

@pytest.mark.asyncio
async def test_send_digests_skips_when_advisory_lock_not_acquired():
    """Prod 2 uvicorn worker'ı ile çalışıyor, ikisi de aynı anda dijest
    döngüsüne uyanıyor. Postgres advisory lock'u alamayan worker (ör. diğer
    worker zaten gönderiyor) hiç mail göndermemeli — eskiden ikisi de
    gönderiyordu, abone günde 2 mail alıyordu."""
    from src.adapters.scheduling.newsletter_job import _send_digests

    mock_email = MagicMock()
    mock_email.send_digest.return_value = True

    with patch("src.adapters.scheduling.newsletter_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.newsletter_job.NewsRepository") as MockNewsRepo, \
         patch("src.adapters.scheduling.newsletter_job.SubscriberRepository") as MockSubRepo:

        db = MagicMock()
        db.execute.return_value.scalar.return_value = False  # kilit başka worker'da
        MockSession.return_value = db

        news_repo = MagicMock()
        news_repo.get_latest_news.return_value = [_article()]
        MockNewsRepo.return_value = news_repo

        from src.domain.models.subscriber import Subscriber
        sub_repo = MagicMock()
        sub_repo.get_active_subscribers.return_value = [Subscriber(email="x@test.com", frequency="daily")]
        MockSubRepo.return_value = sub_repo

        await _send_digests(mock_email)

    mock_email.send_digest.assert_not_called()


@pytest.mark.asyncio
async def test_send_digests_releases_lock_after_sending():
    """Kilidi alan worker işini bitirince serbest bırakmalı — yoksa ertesi gün
    hiçbir worker dijest gönderemez (aynı pooled bağlantı kilidi hep tutar)."""
    from src.adapters.scheduling.newsletter_job import _send_digests, _DIGEST_LOCK_KEY

    mock_email = MagicMock()
    mock_email.send_digest.return_value = True

    with patch("src.adapters.scheduling.newsletter_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.newsletter_job.NewsRepository") as MockNewsRepo, \
         patch("src.adapters.scheduling.newsletter_job.SubscriberRepository") as MockSubRepo, \
         patch("src.adapters.scheduling.newsletter_job.get_active_sponsor", return_value=None):

        db = MagicMock()
        db.execute.return_value.scalar.return_value = True  # kilit alındı
        MockSession.return_value = db

        news_repo = MagicMock()
        news_repo.get_latest_news.return_value = [_article()]
        MockNewsRepo.return_value = news_repo

        from src.domain.models.subscriber import Subscriber
        sub_repo = MagicMock()
        sub_repo.get_active_subscribers.return_value = [Subscriber(email="x@test.com", frequency="daily")]
        MockSubRepo.return_value = sub_repo

        await _send_digests(mock_email)

    unlock_calls = [c for c in db.execute.call_args_list if "pg_advisory_unlock" in str(c.args[0])]
    assert len(unlock_calls) == 1
    assert unlock_calls[0].args[1] == {"key": _DIGEST_LOCK_KEY}


@pytest.mark.asyncio
async def test_send_digests_sends_different_articles_per_subscriber_preference():
    """İki farklı tercihi olan abone, aynı gönderimde farklı haber listesi almalı."""
    from src.adapters.scheduling.newsletter_job import _send_digests
    from src.domain.models.subscriber import Subscriber

    sports = _article("Maç sonucu", topic="Sports")
    politics = _article("Seçim sonucu", topic="Politics")

    mock_email = MagicMock()
    mock_email.send_digest.return_value = True

    with patch("src.adapters.scheduling.newsletter_job.SessionLocal") as MockSession, \
         patch("src.adapters.scheduling.newsletter_job.NewsRepository") as MockNewsRepo, \
         patch("src.adapters.scheduling.newsletter_job.SubscriberRepository") as MockSubRepo, \
         patch("src.adapters.scheduling.newsletter_job.get_active_sponsor", return_value=None):

        MockSession.return_value = MagicMock()
        news_repo = MagicMock()
        news_repo.get_latest_news.return_value = [sports, politics]
        MockNewsRepo.return_value = news_repo

        sports_fan = Subscriber(email="sports@test.com", frequency="daily", preferred_topics=["Sports"])
        politics_fan = Subscriber(email="politics@test.com", frequency="daily", preferred_topics=["Politics"])
        sub_repo = MagicMock()
        sub_repo.get_active_subscribers.return_value = [sports_fan, politics_fan]
        MockSubRepo.return_value = sub_repo

        await _send_digests(mock_email)

    assert mock_email.send_digest.call_count == 2
    calls_by_email = {c.args[0]: c.args[1] for c in mock_email.send_digest.call_args_list}
    assert calls_by_email["sports@test.com"] == [sports]
    assert calls_by_email["politics@test.com"] == [politics]
