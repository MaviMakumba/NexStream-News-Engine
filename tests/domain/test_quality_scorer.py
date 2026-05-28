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
