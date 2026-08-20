"""tests/adapters/test_groq_query_expander.py"""
from unittest.mock import patch, MagicMock
from src.adapters.analysis.groq_query_expander import GroqQueryExpander
from src.adapters.api.metrics import (
    groq_latency_seconds,
    groq_rate_limit_total,
    query_expansion_total,
)


def _expansion_count(result: str) -> float:
    return query_expansion_total.labels(result=result)._value.get()


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


def test_expand_returns_empty_when_terms_is_string_not_list():
    """Regression test: if LLM returns {"terms": "beykoz"} (string instead of array),
    we should return [] not ['b','e','y','k','o','z'] (character iteration bug)."""
    resp = _mock_response(200, content='{"terms": "beykoz"}')
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("istanbul")
    assert result == [], f"Expected empty list, got {result}"


# ── Metrikler (fail-open Groq yolunun sessiz bozulmasını görünür kılar) ───────


def test_metric_expanded_on_success():
    before = _expansion_count("expanded")
    resp = _mock_response(200, content='{"terms": ["Beykoz"]}')
    with patch("requests.post", return_value=resp):
        GroqQueryExpander().expand("istanbul")
    assert _expansion_count("expanded") == before + 1


def test_metric_empty_when_call_succeeds_with_zero_terms():
    """Başarılı ama 0 terimli yanıt HATA DEĞİLDİR (sorgunun bariz bir ilişkili
    terimi olmayabilir) — ayrı bir etiketle sayılır."""
    before_empty = _expansion_count("empty")
    before_error = _expansion_count("error")
    resp = _mock_response(200, content='{"terms": []}')
    with patch("requests.post", return_value=resp):
        GroqQueryExpander().expand("asdkjf")
    assert _expansion_count("empty") == before_empty + 1
    assert _expansion_count("error") == before_error


def test_metric_error_on_non_200():
    before = _expansion_count("error")
    resp = _mock_response(500, text="sunucu hatası")
    with patch("requests.post", return_value=resp):
        GroqQueryExpander().expand("istanbul")
    assert _expansion_count("error") == before + 1


def test_metric_error_on_exception():
    before = _expansion_count("error")
    with patch("requests.post", side_effect=TimeoutError("timeout")):
        GroqQueryExpander().expand("istanbul")
    assert _expansion_count("error") == before + 1


def test_metric_error_on_malformed_json():
    before = _expansion_count("error")
    resp = _mock_response(200, content="bu JSON değil")
    with patch("requests.post", return_value=resp):
        GroqQueryExpander().expand("istanbul")
    assert _expansion_count("error") == before + 1


def test_rate_limit_counter_increments_on_429():
    before_rl = groq_rate_limit_total._value.get()
    before_err = _expansion_count("error")
    resp = _mock_response(429, text="rate limit")
    with patch("requests.post", return_value=resp):
        GroqQueryExpander().expand("istanbul")
    assert groq_rate_limit_total._value.get() == before_rl + 1
    assert _expansion_count("error") == before_err + 1


def test_latency_histogram_observed():
    before = groq_latency_seconds._sum.get()
    resp = _mock_response(200, content='{"terms": ["Beykoz"]}')
    with patch("requests.post", return_value=resp):
        GroqQueryExpander().expand("istanbul")
    assert groq_latency_seconds._sum.get() >= before


def test_blank_query_records_no_metric():
    """Boş sorgu Groq'a hiç gitmiyor — "deneme" sayılmaz, hiçbir etiket artmaz."""
    before = {r: _expansion_count(r) for r in ("hit", "expanded", "empty", "error")}
    with patch("requests.post") as mock_post:
        GroqQueryExpander().expand("   ")
    mock_post.assert_not_called()
    assert {r: _expansion_count(r) for r in before} == before
