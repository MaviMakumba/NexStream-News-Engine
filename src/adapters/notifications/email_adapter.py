import logging
from typing import List
import requests
from src.domain.models.article import Article
from src.domain.ports.email_port import EmailPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_SENTIMENT_ICON = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}


def _digest_html(articles: List[Article], language: str) -> str:
    header = "Günlük Haber Özeti" if language == "TR" else "Daily News Digest"
    rows = ""
    for a in articles:
        icon = _SENTIMENT_ICON.get(a.sentiment_label or "Neutral", "⚪")
        topic = a.topic or ""
        summary = a.summary or ""
        rows += (
            f"<tr><td style='padding:10px 0;border-bottom:1px solid #eee'>"
            f"<b><a href='{a.url}' style='color:#1a73e8;text-decoration:none'>{a.title}</a></b><br>"
            f"<small style='color:#666'>{icon} {a.source} · {topic}</small><br>"
            f"<span style='color:#444;font-size:14px'>{summary}</span>"
            f"</td></tr>"
        )
    return f"""<html><body style='font-family:sans-serif;max-width:640px;margin:auto'>
<h2 style='color:#1a1a1a'>{header}</h2>
<table width='100%' cellpadding='0' cellspacing='0'>{rows}</table>
<p style='color:#999;font-size:12px;margin-top:24px'>
NexStream · <a href='{{unsubscribe_url}}'>Aboneliği iptal et</a>
</p></body></html>"""


def _alert_html(article: Article, keyword: str, language: str) -> str:
    label = "Anahtar kelime eşleşmesi" if language == "TR" else "Keyword match"
    return f"""<html><body style='font-family:sans-serif;max-width:640px;margin:auto'>
<p style='color:#666'>{label}: <b>{keyword}</b></p>
<h2><a href='{article.url}' style='color:#1a73e8;text-decoration:none'>{article.title}</a></h2>
<p style='color:#555'>{article.source} · {article.topic or ''}</p>
<p>{article.summary or ''}</p>
</body></html>"""


class ConsoleEmailAdapter(EmailPort):
    """Development adapter — logs emails instead of sending them."""

    def send_digest(self, to: str, articles: List[Article], language: str) -> bool:
        logger.info("📧 [CONSOLE] Digest → %s | %d haber", to, len(articles))
        return True

    def send_alert(self, to: str, article: Article, matched_keyword: str) -> bool:
        logger.info("📧 [CONSOLE] Alert → %s | kw=%s | '%s'", to, matched_keyword, article.title)
        return True

    def send_welcome(self, to: str, language: str) -> bool:
        logger.info("📧 [CONSOLE] Welcome → %s | lang=%s", to, language)
        return True


class ResendEmailAdapter(EmailPort):
    """Production adapter using Resend (https://resend.com)."""

    _API_URL = "https://api.resend.com/emails"

    def __init__(self):
        self._api_key = settings.resend_api_key
        self._from = settings.email_from

    def _post(self, to: str, subject: str, html: str) -> bool:
        try:
            r = requests.post(
                self._API_URL,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"from": self._from, "to": [to], "subject": subject, "html": html},
                timeout=10,
            )
            if r.status_code in (200, 201):
                return True
            logger.error("Resend API hatası %s: %s", r.status_code, r.text[:200])
            return False
        except Exception as e:
            logger.error("Email gönderilemedi (%s): %s", to, e)
            return False

    def send_digest(self, to: str, articles: List[Article], language: str) -> bool:
        subject = "NexStream Günlük Özet" if language == "TR" else "NexStream Daily Digest"
        return self._post(to, subject, _digest_html(articles, language))

    def send_alert(self, to: str, article: Article, matched_keyword: str) -> bool:
        subject = f"NexStream Alert: {matched_keyword}"
        language = "TR"
        return self._post(to, subject, _alert_html(article, matched_keyword, language))

    def send_welcome(self, to: str, language: str) -> bool:
        subject = "NexStream'e Hoş Geldiniz!" if language == "TR" else "Welcome to NexStream!"
        body = (
            "<h2>Hoş Geldiniz!</h2><p>Günlük haber özetiniz her sabah 08:00'de gelecek.</p>"
            if language == "TR"
            else "<h2>Welcome!</h2><p>Your daily digest will arrive every morning at 08:00.</p>"
        )
        return self._post(to, subject, f"<html><body>{body}</body></html>")


def get_email_adapter() -> EmailPort:
    if settings.resend_api_key:
        return ResendEmailAdapter()
    return ConsoleEmailAdapter()
