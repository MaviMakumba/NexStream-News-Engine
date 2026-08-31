from src.domain.scoring.trust import compute_trust_score


def test_all_zero_scores_zero():
    assert compute_trust_score(0.0, 0.0, 0) == 0


def test_all_max_scores_hundred():
    assert compute_trust_score(1.0, 1.0, 10) == 100


def test_weights_sum_correctly():
    # quality=1.0 (%35) + credibility=0.0 (%0) + corroboration=0 (%0) = 35
    assert compute_trust_score(1.0, 0.0, 0) == 35


def test_corroboration_caps_at_three():
    # corroboration_count=3 ve 10, İKİSİ de tam %20 katkı vermeli (tavanlı)
    assert compute_trust_score(0.0, 0.0, 3) == compute_trust_score(0.0, 0.0, 10) == 20


def test_none_quality_and_credibility_use_neutral_default():
    # None -> 0.5 varsayılan, corroboration=0 -> 100*(0.35*0.5 + 0.45*0.5) = 40
    assert compute_trust_score(None, None, 0) == 40


def test_zero_is_not_treated_as_none():
    # credibility_score=0.0 GERÇEK bir değer, 0.5'e "or" ile geri düşmemeli
    low = compute_trust_score(0.5, 0.0, 0)
    neutral = compute_trust_score(0.5, None, 0)
    assert low < neutral


def test_result_is_always_int():
    result = compute_trust_score(0.73, 0.61, 2)
    assert isinstance(result, int)
