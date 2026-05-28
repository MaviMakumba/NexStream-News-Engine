import pytest
from unittest.mock import patch, MagicMock
from src.adapters.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from src.domain.ports.analysis_port import AnalysisError


def _resp(content, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = [{"generated_text": content}]
    m.raise_for_status = MagicMock()
    return m


def _analyzer(key="hf-key"):
    a = HuggingFaceAnalyzer()
    a.api_key = key
    return a


def test_raises_without_api_key():
    with pytest.raises(AnalysisError):
        _analyzer(key="").analyze_or_raise("text")


def test_analyze_text_returns_neutral_without_key():
    result = _analyzer(key="").analyze_text("some text")
    assert result["sentiment_label"] == "Neutral"


def test_parses_successful_response():
    content = ('{"sentiment_score": 0.8, "sentiment_label": "Positive", "summary": "ok", '
               '"entities": {"persons": ["Ali"], "organizations": [], "locations": []}, "topic": "Sports"}')
    with patch("requests.post", return_value=_resp(content)):
        result = _analyzer().analyze_or_raise("Beşiktaş kazandı")

    assert result["sentiment_label"] == "Positive"
    assert result["sentiment_score"] == 0.8
    assert result["topic"] == "Sports"
    assert result["entities"]["persons"] == ["Ali"]


def test_handles_dict_response_shape():
    content = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "s"}'
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"generated_text": content}
    resp.raise_for_status = MagicMock()
    with patch("requests.post", return_value=resp):
        result = _analyzer().analyze_or_raise("text")

    assert result["sentiment_label"] == "Neutral"


def test_raises_on_persistent_failure():
    with patch("requests.post", side_effect=Exception("conn error")):
        with pytest.raises(AnalysisError):
            _analyzer().analyze_or_raise("text")


def test_analyze_text_returns_neutral_on_failure():
    with patch("requests.post", side_effect=Exception("conn error")):
        result = _analyzer().analyze_text("some news text here")
    assert result["sentiment_label"] == "Neutral"
    assert result["summary"] == "some news text here"


def test_retries_on_503_model_loading():
    loading = MagicMock()
    loading.status_code = 503
    loading.headers = {"retry-after": "1"}
    loading.raise_for_status = MagicMock()
    success = _resp('{"sentiment_score": 0.3, "sentiment_label": "Positive", "summary": "s"}')
    with patch("requests.post", side_effect=[loading, success]):
        with patch("time.sleep"):
            result = _analyzer().analyze_or_raise("text")

    assert result["sentiment_label"] == "Positive"
