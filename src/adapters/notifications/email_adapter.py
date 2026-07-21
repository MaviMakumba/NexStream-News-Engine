"""E-posta adapter'ları — EmailPort'un iki implementasyonu + seçici factory.

ResendEmailAdapter gerçek gönderim yapar (RESEND_API_KEY gerekli);
ConsoleEmailAdapter sadece loglar (lokal geliştirme). get_email_adapter()
ortama göre doğru olanı seçer — çağıran kod farkı bilmez.

i18n: tüm çeviriler `_STRINGS`/`_TOPIC_LABELS` sözlüklerinde toplanır —
frontend/lib/i18n.ts::UI ile aynı desen. Yeni bir dil eklemek (örn. Fransızca)
sadece bu iki sözlüğe bir `"FR": {...}` bloğu eklemek demektir; hiçbir
`if language == "TR" else ...` dallanmasına dokunulmaz.
"""

import html
import logging
from typing import List
from urllib.parse import quote
import requests
from src.domain.models.article import Article
from src.domain.ports.email_port import EmailPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_DEFAULT_LANG = "TR"

_SENTIMENT_ICON = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}

_STRINGS: dict = {
    "TR": {
        "digest_subject": "NexStream Günlük Özet",
        "digest_header": "Günlük Haber Özeti",
        "unsubscribe": "Aboneliği iptal et",
        "sponsor_label": "Bu haftanın sponsoru",
        "alert_subject_prefix": "NexStream Uyarı",
        "alert_keyword_label": "Anahtar kelime eşleşmesi",
        "welcome_subject": "NexStream'e Hoş Geldiniz!",
        "welcome_title": "Hoş Geldiniz!",
        "welcome_body": "Günlük haber özetiniz her sabah 09:00'da gelecek.",
        "reset_subject": "NexStream Şifre Sıfırlama",
        "reset_title": "Şifre Sıfırlama",
        "reset_body": "Hesabınız için bir şifre sıfırlama talebi aldık. Aşağıdaki butona tıklayarak yeni bir şifre belirleyebilirsiniz.",
        "reset_cta": "Şifremi Sıfırla",
        "reset_expiry": "Bu bağlantı 1 saat içinde geçerliliğini yitirir. Bu talebi siz yapmadıysanız bu maili yok sayabilirsiniz.",
        "verify_subject": "NexStream E-posta Doğrulama",
        "verify_title": "E-posta Adresini Doğrula",
        "verify_body": "Hesabını kullanmaya devam edebilirsin, ama Pro/Kurumsal'a yükseltmeden önce e-posta adresini doğrulaman gerekiyor. Aşağıdaki butona tıkla.",
        "verify_cta": "E-postamı Doğrula",
        "verify_expiry": "Bu bağlantı 24 saat içinde geçerliliğini yitirir. Bu kaydı siz yapmadıysanız bu maili yok sayabilirsiniz.",
    },
    "EN": {
        "digest_subject": "NexStream Daily Digest",
        "digest_header": "Daily News Digest",
        "unsubscribe": "Unsubscribe",
        "sponsor_label": "This week's sponsor",
        "alert_subject_prefix": "NexStream Alert",
        "alert_keyword_label": "Keyword match",
        "welcome_subject": "Welcome to NexStream!",
        "welcome_title": "Welcome!",
        "welcome_body": "Your daily digest will arrive every morning at 09:00.",
        "reset_subject": "NexStream Password Reset",
        "reset_title": "Password Reset",
        "reset_body": "We received a request to reset your password. Click the button below to choose a new one.",
        "reset_cta": "Reset Password",
        "reset_expiry": "This link expires in 1 hour. If you didn't request this, you can safely ignore this email.",
        "verify_subject": "NexStream Email Verification",
        "verify_title": "Verify Your Email",
        "verify_body": "You can keep using your account, but verifying your email is required before upgrading to Pro/Enterprise. Click the button below.",
        "verify_cta": "Verify My Email",
        "verify_expiry": "This link expires in 24 hours. If you didn't create this account, you can safely ignore this email.",
    },
}

# Frontend'in lib/i18n.ts::TOPIC_LABELS'iyle birebir aynı yapı — haber konuları
# backend'de İngilizce sabit değer olarak saklanır (Sports, Technology, ...),
# e-postada abonenin dil tercihine göre çevrilir.
_TOPIC_LABELS: dict = {
    "TR": {
        "Technology": "Teknoloji", "Sports": "Spor", "Economy": "Ekonomi",
        "Politics": "Siyaset", "Health": "Sağlık", "Culture": "Kültür",
        "World": "Dünya", "Other": "Diğer",
    },
    "EN": {
        "Technology": "Technology", "Sports": "Sports", "Economy": "Economy",
        "Politics": "Politics", "Health": "Health", "Culture": "Culture",
        "World": "World", "Other": "Other",
    },
}


def _t(language: str, key: str) -> str:
    """Sözlük tabanlı çeviri — bilinmeyen dil `_DEFAULT_LANG`'a düşer."""
    return _STRINGS.get(language, _STRINGS[_DEFAULT_LANG])[key]


def _topic_label(topic: str, language: str) -> str:
    if not topic:
        return ""
    labels = _TOPIC_LABELS.get(language, _TOPIC_LABELS[_DEFAULT_LANG])
    return labels.get(topic, topic)


def _unsubscribe_url(email: str, language: str) -> str:
    return f"{settings.api_base_url}/subscriptions/unsubscribe?email={quote(email)}&lang={quote(language)}"


def _sponsor_html(sponsor, language: str) -> str:
    if not sponsor:
        return ""
    label = _t(language, "sponsor_label")
    return (
        f"<div style='background:#f0f7ff;border-left:4px solid #1a73e8;padding:12px 16px;margin:16px 0'>"
        f"<small style='color:#888;text-transform:uppercase;letter-spacing:1px'>{label}</small><br>"
        f"<b><a href='{html.escape(sponsor.url)}' style='color:#1a73e8;text-decoration:none'>{html.escape(sponsor.name)}</a></b><br>"
        f"<span style='color:#444;font-size:14px'>{html.escape(sponsor.message)}</span>"
        f"</div>"
    )


def _digest_html(to: str, articles: List[Article], language: str, sponsor=None) -> str:
    header = _t(language, "digest_header")
    unsubscribe_label = _t(language, "unsubscribe")
    rows = ""
    for a in articles:
        icon = _SENTIMENT_ICON.get(a.sentiment_label or "Neutral", "⚪")
        # a.title/a.summary/a.source dış kaynaklı (RSS feed'inden) — güvenlik denetimi:
        # escape edilmeden HTML'e gömülüyordu, ele geçirilmiş bir kaynak phishing linki
        # enjekte edip tüm abonelere gönderebilirdi.
        topic = html.escape(_topic_label(a.topic, language))
        title = html.escape(a.title)
        source = html.escape(a.source)
        url = html.escape(a.url)
        summary = html.escape(a.summary or "")
        rows += (
            f"<tr><td style='padding:10px 0;border-bottom:1px solid #eee'>"
            f"<b><a href='{url}' style='color:#1a73e8;text-decoration:none'>{title}</a></b><br>"
            f"<small style='color:#666'>{icon} {source} · {topic}</small><br>"
            f"<span style='color:#444;font-size:14px'>{summary}</span>"
            f"</td></tr>"
        )
    sponsor_section = _sponsor_html(sponsor, language)
    return f"""<html><body style='font-family:sans-serif;max-width:640px;margin:auto'>
<h2 style='color:#1a1a1a'>{header}</h2>
{sponsor_section}
<table width='100%' cellpadding='0' cellspacing='0'>{rows}</table>
<p style='color:#999;font-size:12px;margin-top:24px'>
NexStream · <a href='{_unsubscribe_url(to, language)}' style='color:#999;text-decoration:underline'>{unsubscribe_label}</a>
</p></body></html>"""


def _password_reset_html(reset_url: str, language: str) -> str:
    title, body, cta, expiry = (
        _t(language, "reset_title"), _t(language, "reset_body"),
        _t(language, "reset_cta"), _t(language, "reset_expiry"),
    )
    return f"""<html><body style='font-family:sans-serif;max-width:640px;margin:auto'>
<h2 style='color:#1a1a1a'>{title}</h2>
<p style='color:#444'>{body}</p>
<p><a href='{reset_url}' style='display:inline-block;background:#1a73e8;color:#fff;text-decoration:none;
padding:12px 24px;border-radius:6px;font-weight:600'>{cta}</a></p>
<p style='color:#999;font-size:12px;margin-top:24px'>{expiry}</p>
</body></html>"""


def _verification_html(verify_url: str, language: str) -> str:
    title, body, cta, expiry = (
        _t(language, "verify_title"), _t(language, "verify_body"),
        _t(language, "verify_cta"), _t(language, "verify_expiry"),
    )
    return f"""<html><body style='font-family:sans-serif;max-width:640px;margin:auto'>
<h2 style='color:#1a1a1a'>{title}</h2>
<p style='color:#444'>{body}</p>
<p><a href='{verify_url}' style='display:inline-block;background:#1a73e8;color:#fff;text-decoration:none;
padding:12px 24px;border-radius:6px;font-weight:600'>{cta}</a></p>
<p style='color:#999;font-size:12px;margin-top:24px'>{expiry}</p>
</body></html>"""


def _alert_html(article: Article, keyword: str, language: str) -> str:
    label = _t(language, "alert_keyword_label")
    topic = html.escape(_topic_label(article.topic, language))
    return f"""<html><body style='font-family:sans-serif;max-width:640px;margin:auto'>
<p style='color:#666'>{label}: <b>{html.escape(keyword)}</b></p>
<h2><a href='{html.escape(article.url)}' style='color:#1a73e8;text-decoration:none'>{html.escape(article.title)}</a></h2>
<p style='color:#555'>{html.escape(article.source)} · {topic}</p>
<p>{html.escape(article.summary or '')}</p>
</body></html>"""


def _welcome_html(language: str) -> str:
    title, body = _t(language, "welcome_title"), _t(language, "welcome_body")
    return f"<html><body style='font-family:sans-serif'><h2>{title}</h2><p>{body}</p></body></html>"


class ConsoleEmailAdapter(EmailPort):
    """Development adapter — logs emails instead of sending them."""

    def send_digest(self, to: str, articles: List[Article], language: str, sponsor=None) -> bool:
        logger.info("📧 [CONSOLE] Digest → %s | %d haber | sponsor=%s", to, len(articles), sponsor.name if sponsor else None)
        return True

    def send_alert(self, to: str, article: Article, matched_keyword: str, language: str) -> bool:
        logger.info("📧 [CONSOLE] Alert → %s | kw=%s | '%s'", to, matched_keyword, article.title)
        return True

    def send_welcome(self, to: str, language: str) -> bool:
        logger.info("📧 [CONSOLE] Welcome → %s | lang=%s", to, language)
        return True

    def send_password_reset(self, to: str, reset_url: str, language: str) -> bool:
        logger.info("📧 [CONSOLE] Password reset → %s | %s", to, reset_url)
        return True

    def send_verification(self, to: str, verify_url: str, language: str) -> bool:
        logger.info("📧 [CONSOLE] Email verification → %s | %s", to, verify_url)
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

    def send_digest(self, to: str, articles: List[Article], language: str, sponsor=None) -> bool:
        return self._post(to, _t(language, "digest_subject"), _digest_html(to, articles, language, sponsor))

    def send_alert(self, to: str, article: Article, matched_keyword: str, language: str) -> bool:
        subject = f"{_t(language, 'alert_subject_prefix')}: {matched_keyword}"
        return self._post(to, subject, _alert_html(article, matched_keyword, language))

    def send_welcome(self, to: str, language: str) -> bool:
        return self._post(to, _t(language, "welcome_subject"), _welcome_html(language))

    def send_password_reset(self, to: str, reset_url: str, language: str) -> bool:
        return self._post(to, _t(language, "reset_subject"), _password_reset_html(reset_url, language))

    def send_verification(self, to: str, verify_url: str, language: str) -> bool:
        return self._post(to, _t(language, "verify_subject"), _verification_html(verify_url, language))


def get_email_adapter() -> EmailPort:
    if settings.resend_api_key:
        return ResendEmailAdapter()
    return ConsoleEmailAdapter()
