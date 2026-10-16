from src.domain.scoring.quality import compute_quality_score
from src.domain.models.article import Article


def _art(title="A reasonably long news headline", content="x" * 600, summary="x" * 30, entities=None):
    return Article(title=title, source="BBC", url="u", content=content, summary=summary, entities=entities)


def test_empty_article_scores_zero():
    a = Article(title="", source="BBC", url="u", content="", summary=None, entities=None)
    assert compute_quality_score(a) == 0.0


def test_full_article_scores_one():
    a = _art(
        title="A reasonably long news headline",
        content="x" * 600,
        summary="x" * 30,
        entities={"persons": ["A", "B", "C"], "organizations": ["D", "E"], "locations": []},
    )
    assert compute_quality_score(a) == 1.0


def test_score_within_bounds():
    assert 0.0 <= compute_quality_score(_art()) <= 1.0


def test_longer_content_scores_higher():
    short = _art(content="x" * 100, summary=None, entities=None, title="x")
    long = _art(content="x" * 600, summary=None, entities=None, title="x")
    assert compute_quality_score(long) > compute_quality_score(short)


def test_more_entities_scores_higher():
    few = _art(content="x" * 100, summary=None, title="x",
               entities={"persons": ["A"], "organizations": [], "locations": []})
    many = _art(content="x" * 100, summary=None, title="x",
                entities={"persons": ["A", "B", "C", "D", "E"], "organizations": [], "locations": []})
    assert compute_quality_score(many) > compute_quality_score(few)


def test_missing_summary_lowers_score():
    assert compute_quality_score(_art(summary="x" * 30)) > compute_quality_score(_art(summary=None))


def test_none_entities_does_not_raise():
    assert compute_quality_score(_art(entities=None)) >= 0.0


# ── Sınır değerleri (7 Eki 2026 mutasyon denetimi: eşikler hiç sabitlenmemişti) ──

def _only(**kw):
    base = dict(title="", content="", summary=None, entities=None)
    base.update(kw)
    return Article(source="BBC", url="u", **base)


def test_length_component_is_capped_at_its_weight():
    assert compute_quality_score(_only(content="x" * 5000)) == 0.40


def test_entity_component_is_capped_at_its_weight():
    many = {"persons": [str(i) for i in range(20)]}
    assert compute_quality_score(_only(entities=many)) == 0.35


def test_entity_component_is_proportional_below_cap():
    assert compute_quality_score(_only(entities={"persons": ["a", "b"]})) == 0.14


def test_summary_threshold_is_exactly_20_characters():
    assert compute_quality_score(_only(summary="x" * 19)) == 0.0
    assert compute_quality_score(_only(summary="x" * 20)) == 0.15


def test_title_range_is_15_to_200_inclusive():
    assert compute_quality_score(_only(title="x" * 14)) == 0.0
    assert compute_quality_score(_only(title="x" * 15)) == 0.10
    assert compute_quality_score(_only(title="x" * 200)) == 0.10
    assert compute_quality_score(_only(title="x" * 201)) == 0.0


def test_score_is_rounded_to_four_decimals():
    assert compute_quality_score(_only(content="x")) == 0.0007
