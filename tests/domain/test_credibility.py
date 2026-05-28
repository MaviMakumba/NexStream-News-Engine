from src.domain.scoring.credibility import (
    base_credibility, compute_credibility, SOURCE_CREDIBILITY, DEFAULT_CREDIBILITY,
)


def test_known_source_returns_seeded_value():
    assert base_credibility("BBC Technology") == 0.90
    assert base_credibility("Hacker News") == 0.60


def test_unknown_source_returns_default():
    assert base_credibility("Bilinmeyen Kaynak") == DEFAULT_CREDIBILITY
    assert base_credibility("Bilinmeyen Kaynak") == 0.50


def test_no_corroboration_equals_base():
    assert compute_credibility(0.7, 0) == 0.7


def test_credibility_increases_with_corroboration():
    assert compute_credibility(0.7, 2) == 0.80  # 0.7 + 2 * 0.05


def test_corroboration_boost_capped():
    assert compute_credibility(0.7, 100) == 0.90  # boost cap 0.20


def test_credibility_never_exceeds_one():
    assert compute_credibility(0.95, 100) == 1.0


def test_negative_corroboration_treated_as_zero():
    assert compute_credibility(0.6, -5) == 0.6


def test_all_seeded_sources_in_valid_range():
    for source, score in SOURCE_CREDIBILITY.items():
        assert 0.0 <= score <= 1.0, source
