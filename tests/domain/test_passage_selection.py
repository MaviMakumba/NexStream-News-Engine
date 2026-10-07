import pytest

from src.domain.services.passage_selection import (
    MAX_PARAGRAPHS,
    MAX_PARAGRAPH_CHARS,
    cosine_similarity,
    estimate_tokens,
    select_passages,
    split_paragraphs,
)

P1 = "Birinci paragraf, yeterince uzun bir cümleden oluşuyor ve filtreyi geçer."
P2 = "İkinci paragraf, oyuncunun sakatlığı hakkında kulüp doktorunun açıklamasını içerir."
P3 = "Üçüncü paragraf, bilet fiyatları ve stat doluluğu hakkında alakasız bilgi verir."


def test_split_paragraphs_drops_short_lines_and_collapses_whitespace():
    text = f"Kısa\n\n{P1}\n   \n  {P2.replace(' ', '   ')}  \n"
    assert split_paragraphs(text) == [P1, P2]


def test_split_paragraphs_truncates_long_paragraph_and_caps_count():
    long = "a" * (MAX_PARAGRAPH_CHARS + 500)
    assert split_paragraphs(long) == ["a" * MAX_PARAGRAPH_CHARS]
    many = "\n".join(f"{P1} {i}" for i in range(MAX_PARAGRAPHS + 20))
    assert len(split_paragraphs(many)) == MAX_PARAGRAPHS


def test_split_paragraphs_empty_text():
    assert split_paragraphs("") == []


def test_estimate_tokens_is_conservative_ceiling():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abc") == 1
    assert estimate_tokens("abcd") == 2


def test_cosine_similarity_basic_and_zero_vector():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([0, 0], [1, 0]) == 0.0


def test_select_passages_picks_most_similar_within_budget_in_original_order():
    paragraphs = [P1, P2, P3]
    vectors = [[0, 1], [1, 0], [0.7, 0.7]]
    # her paragraf ~25 token; bütçe 55 -> yalnız en benzer ikisi (P2, P3) sığar
    chosen = select_passages(paragraphs, [1, 0], vectors, token_budget=55)
    assert chosen == [P2, P3]


def test_select_passages_skips_paragraph_that_does_not_fit_but_keeps_looking():
    big = "x" * 300  # ~100 token
    chosen = select_passages([big, P2], [1, 0], [[1, 0], [0.5, 0.5]], token_budget=40)
    assert chosen == [P2]


def test_select_passages_truncates_best_when_nothing_fits_budget():
    big = "y" * 300
    chosen = select_passages([big], [1, 0], [[1, 0]], token_budget=10)
    assert len(chosen) == 1 and len(chosen[0]) == 10 * 3


def test_select_passages_empty_and_mismatched_inputs():
    assert select_passages([], [1, 0], [], token_budget=100) == []
    with pytest.raises(ValueError):
        select_passages([P1, P2], [1, 0], [[1, 0]], token_budget=100)
