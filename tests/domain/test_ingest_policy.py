from datetime import datetime, timedelta, timezone

from src.domain.models.article import Article
from src.domain.policies.ingest_policy import select_for_analysis, sort_newest_first

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


def _a(name, hours_ago=None, naive=False):
    published = None
    if hours_ago is not None:
        published = NOW - timedelta(hours=hours_ago)
        if naive:
            published = published.replace(tzinfo=None)
    return Article(title=name, source="S", url=f"http://x/{name}", content="c", published_at=published)


def _titles(articles):
    return [a.title for a in articles]


def _select(articles, **kw):
    params = dict(now=NOW, max_age_hours=48, daily_budget_left=None, per_run_limit=None)
    params.update(kw)
    return select_for_analysis(articles, **params)


def test_sort_newest_first_puts_undated_last_and_is_stable():
    ordered = sort_newest_first([_a("old", 30), _a("undated1"), _a("new", 1), _a("undated2"), _a("mid", 10)])
    assert _titles(ordered) == ["new", "mid", "old", "undated1", "undated2"]


def test_naive_datetimes_are_treated_as_utc_and_do_not_crash():
    ordered = sort_newest_first([_a("aware_old", 5), _a("naive_new", 1, naive=True)])
    assert _titles(ordered) == ["naive_new", "aware_old"]


def test_articles_older_than_max_age_are_dropped_but_undated_are_kept():
    picked = _select([_a("fresh", 47), _a("stale", 49), _a("undated")])
    assert _titles(picked) == ["fresh", "undated"]


def test_freshest_are_selected_first_when_budget_is_tight():
    picked = _select([_a("c", 20), _a("a", 1), _a("b", 5)], per_run_limit=2)
    assert _titles(picked) == ["a", "b"]


def test_daily_budget_exhausted_selects_nothing():
    for left in (0, -3):
        assert _select([_a("a", 1)], daily_budget_left=left) == []


def test_smaller_of_daily_budget_and_per_run_limit_wins():
    arts = [_a(str(i), i) for i in range(1, 8)]
    assert len(_select(arts, daily_budget_left=3, per_run_limit=5)) == 3
    assert len(_select(arts, daily_budget_left=6, per_run_limit=4)) == 4


def test_none_means_unlimited():
    assert len(_select([_a(str(i), i) for i in range(1, 10)])) == 9
