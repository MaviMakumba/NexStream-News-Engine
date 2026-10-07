"""Sayfalama imleci — doğrudan birim testleri (önceden yalnız router testinden
dolaylı: mikrosaniye hesabı ve sabitler korunmuyordu)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.domain.news_cursor import decode_cursor, effective_date, encode_cursor, legacy_cursor_id

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _micros(dt):
    return (dt - _EPOCH) // timedelta(microseconds=1)


def _article(published_at=None, created_at=None, id=42):
    return SimpleNamespace(
        id=id, published_at=published_at,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_encode_is_epoch_microseconds_then_id():
    dt = datetime(2026, 10, 7, 12, 0, 0, 123456, tzinfo=timezone.utc)
    assert encode_cursor(_article(published_at=dt)) == f"{_micros(dt)}_42"


def test_round_trip_keeps_microseconds_and_id():
    dt = datetime(2026, 10, 7, 12, 0, 0, 999999, tzinfo=timezone.utc)
    assert decode_cursor(encode_cursor(_article(published_at=dt, id=7))) == (dt, 7)


def test_naive_datetime_is_treated_as_utc():
    naive = datetime(2026, 10, 7, 12, 0, 0, 5)
    aware = naive.replace(tzinfo=timezone.utc)
    assert encode_cursor(_article(published_at=naive)) == encode_cursor(_article(published_at=aware))


def test_published_at_wins_over_created_at():
    pub = datetime(2026, 5, 1, tzinfo=timezone.utc)
    art = _article(published_at=pub, created_at=datetime(2026, 9, 1, tzinfo=timezone.utc))
    assert effective_date(art) == pub


def test_falls_back_to_created_at_without_published_at():
    created = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert effective_date(_article(published_at=None, created_at=created)) == created


def test_cursor_without_separator_is_invalid():
    with pytest.raises(ValueError):
        decode_cursor("12345")


def test_legacy_numeric_cursor_is_recognised_new_one_is_not():
    assert legacy_cursor_id("123") == 123
    assert legacy_cursor_id("1791358465000000_123") is None
