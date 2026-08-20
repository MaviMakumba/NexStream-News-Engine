"""tests/adapters/test_groq_query_expander.py"""
from unittest.mock import patch, MagicMock
from src.adapters.analysis.groq_query_expander import GroqQueryExpander


def _mock_response(status_code=200, content=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    if content is not None:
        r.json.return_value = {"choices": [{"message": {"content": content}}]}
    return r


def test_expand_returns_terms_on_success():
    resp = _mock_response(200, content='{"terms": ["Beykoz", "Kadıköy", "Üsküdar"]}')
    with patch("requests.post", return_value=resp) as mock_post:
        expander = GroqQueryExpander()
        result = expander.expand("istanbul")
    assert result == ["Beykoz", "Kadıköy", "Üsküdar"]
    mock_post.assert_called_once()


def test_expand_extracts_json_even_with_surrounding_text():
    resp = _mock_response(200, content='Elbette:\n{"terms": ["Beşiktaş", "Fenerbahçe"]}\nUmarım yardımcı olur.')
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("futbol")
    assert result == ["Beşiktaş", "Fenerbahçe"]


def test_expand_returns_empty_on_non_200():
    resp = _mock_response(429, text="rate limit")
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("istanbul")
    assert result == []


def test_expand_returns_empty_on_malformed_json():
    resp = _mock_response(200, content="bu JSON değil, düz metin")
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("istanbul")
    assert result == []


def test_expand_returns_empty_on_request_exception():
    with patch("requests.post", side_effect=TimeoutError("timeout")):
        result = GroqQueryExpander().expand("istanbul")
    assert result == []


def test_expand_returns_empty_for_blank_query():
    with patch("requests.post") as mock_post:
        result = GroqQueryExpander().expand("   ")
    assert result == []
    mock_post.assert_not_called()


def test_expand_limits_to_six_terms():
    terms = [f"terim{i}" for i in range(10)]
    resp = _mock_response(200, content=f'{{"terms": {terms!r}}}'.replace("'", '"'))
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("test")
    assert len(result) <= 6


def test_expand_filters_non_string_terms():
    resp = _mock_response(200, content='{"terms": ["Beykoz", 123, null, "  ", "Kadıköy"]}')
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("istanbul")
    assert result == ["Beykoz", "Kadıköy"]
