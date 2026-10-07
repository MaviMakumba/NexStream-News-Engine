from src.adapters.analysis.token_budget import RollingTokenBudget


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_has_room_until_limit_is_reached():
    budget = RollingTokenBudget(limit=1000, clock=Clock())
    assert budget.has_room()
    budget.record(600)
    assert budget.has_room()
    budget.record(400)
    assert not budget.has_room()


def test_usage_ages_out_of_the_rolling_window():
    clock = Clock()
    budget = RollingTokenBudget(limit=1000, window_seconds=100, clock=clock)
    budget.record(1000)
    assert not budget.has_room()

    clock.now = 101
    assert budget.has_room()


def test_only_expired_part_of_usage_is_released():
    clock = Clock()
    budget = RollingTokenBudget(limit=1000, window_seconds=100, clock=clock)
    budget.record(600)
    clock.now = 60
    budget.record(500)  # toplam 1100 -> dolu

    clock.now = 101  # ilk 600 düştü, geriye 500
    assert budget.has_room()
    assert budget.used() == 500


def test_default_window_is_24_hours():
    """Groq TPD'si kayan 24 saat — varsayılan pencere bu olmalı."""
    clock = Clock()
    budget = RollingTokenBudget(limit=100, clock=clock)
    budget.record(100)

    clock.now = 86399
    assert not budget.has_room()
    clock.now = 86400
    assert budget.has_room()


def test_usage_exactly_at_window_edge_is_expired():
    """Tam pencere sınırındaki kayıt artık sayılmaz (sınır dışı)."""
    for now, expected in [(99.9, 100), (100, 0)]:
        clock = Clock()
        budget = RollingTokenBudget(limit=100, window_seconds=100, clock=clock)
        budget.record(100)
        clock.now = now
        assert budget.used() == expected
