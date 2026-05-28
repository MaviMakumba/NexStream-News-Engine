import pytest
from unittest.mock import MagicMock
from src.domain.ports.analysis_port import AnalysisPort, AnalysisError
from src.adapters.analysis.fallback_analyzer import FallbackAnalyzer


_GOOD = {
    "sentiment_score": 0.5, "sentiment_label": "Positive", "summary": "s",
    "entities": {"persons": [], "organizations": [], "locations": []}, "topic": "Other",
}


def _ok(result):
    a = MagicMock(spec=AnalysisPort)
    a.analyze_or_raise.return_value = result
    return a


def _fail():
    a = MagicMock(spec=AnalysisPort)
    a.analyze_or_raise.side_effect = AnalysisError("boom")
    return a


def test_requires_at_least_one_analyzer():
    with pytest.raises(ValueError):
        FallbackAnalyzer([])


def test_returns_first_successful_and_skips_rest():
    primary = _ok(_GOOD)
    secondary = _ok({"other": True})
    fb = FallbackAnalyzer([primary, secondary])

    assert fb.analyze_text("x") == _GOOD
    secondary.analyze_or_raise.assert_not_called()


def test_falls_back_to_second_when_first_fails():
    primary, secondary = _fail(), _ok(_GOOD)
    fb = FallbackAnalyzer([primary, secondary])

    assert fb.analyze_text("x") == _GOOD
    primary.analyze_or_raise.assert_called_once()
    secondary.analyze_or_raise.assert_called_once()


def test_neutral_fallback_when_all_fail():
    fb = FallbackAnalyzer([_fail(), _fail()])

    result = fb.analyze_text("Some text")

    assert result["sentiment_label"] == "Neutral"
    assert result["sentiment_score"] == 0.0
    assert result["topic"] == "Other"
    assert result["entities"] == {"persons": [], "organizations": [], "locations": []}


def test_analyze_or_raise_raises_when_all_fail():
    fb = FallbackAnalyzer([_fail()])
    with pytest.raises(AnalysisError):
        fb.analyze_or_raise("x")
