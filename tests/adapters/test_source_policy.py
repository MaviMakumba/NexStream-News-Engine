import logging

from src.adapters.scrapers.source_policy import effective_daily_cap, parse_cap_overrides


def test_valid_json_overrides_are_parsed():
    assert parse_cap_overrides('{"CNN Türk": 80, "Sözcü": 50}') == {"CNN Türk": 80, "Sözcü": 50}


def test_empty_setting_means_no_overrides():
    assert parse_cap_overrides("") == {}
    assert parse_cap_overrides("   ") == {}


def test_broken_json_falls_back_to_defaults_with_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        assert parse_cap_overrides("{not json") == {}
    assert "SOURCE_DAILY_CAPS" in caplog.text


def test_non_object_json_is_rejected():
    assert parse_cap_overrides("[1, 2]") == {}


def test_invalid_values_are_skipped_but_valid_ones_survive(caplog):
    with caplog.at_level(logging.WARNING):
        result = parse_cap_overrides('{"A": "x", "B": 0, "C": -5, "D": 40, "E": 12.0}')
    assert result == {"D": 40, "E": 12}
    assert "A" in caplog.text


def test_effective_cap_prefers_override_then_default_then_none():
    assert effective_daily_cap("A", 100, {"A": 30}) == 30
    assert effective_daily_cap("A", 100, {}) == 100
    assert effective_daily_cap("A", None, {}) is None
