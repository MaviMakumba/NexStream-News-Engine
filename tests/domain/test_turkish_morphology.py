"""Çekim eki tanıma — doğrudan birim testleri.

Mutasyon denetimi (7 Eki 2026): modül yalnızca subscriber_matching üzerinden
DOLAYLI test ediliyordu (mutant yakalama %47). Ek zinciri sınırı ve dönüş
tipleri hiçbir testte sabitlenmemişti.
"""
from src.domain.services.turkish_morphology import is_inflection_of


def test_term_itself_is_an_inflection():
    assert is_inflection_of("tren", "tren") is True


def test_real_inflections_are_accepted():
    for word in ["trenler", "trenin", "trende", "trenlerimizdekiler"]:
        assert is_inflection_of("tren", word) is True, word


def test_words_that_merely_start_with_the_term_are_rejected():
    for word in ["trendyol", "trend", "trenyolu"]:
        assert is_inflection_of("tren", word) is False, word


def test_word_not_starting_with_term_is_false_not_none():
    assert is_inflection_of("tren", "kedi") is False


def test_five_suffix_chain_is_accepted_six_is_not():
    """Ek zinciri en fazla 5 ek: gerçekçi zincirleri kabul eder, sonsuz
    'ler' yığınlarını reddeder."""
    assert is_inflection_of("x", "x" + "ler" * 5) is True
    assert is_inflection_of("x", "x" + "ler" * 6) is False


def test_unknown_remainder_is_rejected_with_bool():
    assert is_inflection_of("tren", "trenxyz") is False
