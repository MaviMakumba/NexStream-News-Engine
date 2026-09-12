"""Bülten iptal linki imzası (12 Eylül 2026 güvenlik turu).

`GET /subscriptions/unsubscribe?email=...` daha önce SADECE e-posta adresini
alıyordu — adresi bilen herkes başkasını abonelikten çıkarabiliyordu (canlıda
bir "güvenlik araştırmacısı" tarafından denenip mail ile ihbar edildi). Link
artık e-postaya bağlı bir HMAC imzası taşıyor; imza sunucu secret'ı olmadan
üretilemez, adres değişince geçersizleşir.
"""

from src.adapters.api.subscription_tokens import make_unsubscribe_token, verify_unsubscribe_token


def test_token_verifies_for_same_email():
    token = make_unsubscribe_token("ali@example.com")
    assert isinstance(token, str) and len(token) >= 32
    assert verify_unsubscribe_token("ali@example.com", token) is True


def test_token_is_deterministic_so_old_email_links_keep_working():
    assert make_unsubscribe_token("ali@example.com") == make_unsubscribe_token("ali@example.com")


def test_token_rejects_other_email():
    token = make_unsubscribe_token("ali@example.com")
    assert verify_unsubscribe_token("veli@example.com", token) is False


def test_token_rejects_tampered_or_missing_value():
    token = make_unsubscribe_token("ali@example.com")
    tampered = ("0" if token[0] != "0" else "1") + token[1:]
    assert verify_unsubscribe_token("ali@example.com", tampered) is False
    assert verify_unsubscribe_token("ali@example.com", "") is False
    assert verify_unsubscribe_token("ali@example.com", None) is False


def test_token_is_case_insensitive_on_email():
    """Kayıt sırasında e-posta lowercase normalize ediliyor ama eski abone
    kayıtları karışık büyük/küçük harfli olabilir — link her iki yazımla da geçmeli."""
    token = make_unsubscribe_token("Ali@Example.com")
    assert verify_unsubscribe_token("ali@example.com", token) is True
