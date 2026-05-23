import pytest
from pydantic import ValidationError
from src.domain.schemas.news_schema import SearchRequest, ScrapeCommand


# ── SearchRequest validation ──────────────────────────────────────────────────

def test_search_request_valid():
    req = SearchRequest(query="yapay zeka", n_results=5)
    assert req.query == "yapay zeka"
    assert req.n_results == 5


def test_search_request_empty_query_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(query="")


def test_search_request_query_too_long_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(query="a" * 201)


def test_search_request_query_max_length_accepted():
    req = SearchRequest(query="a" * 200)
    assert len(req.query) == 200


def test_search_request_n_results_default():
    req = SearchRequest(query="test")
    assert req.n_results == 10


def test_search_request_n_results_min():
    req = SearchRequest(query="test", n_results=1)
    assert req.n_results == 1


def test_search_request_n_results_max():
    req = SearchRequest(query="test", n_results=50)
    assert req.n_results == 50


def test_search_request_n_results_zero_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(query="test", n_results=0)


def test_search_request_n_results_over_50_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(query="test", n_results=51)


def test_search_request_valid_sentiment():
    for label in ("Positive", "Negative", "Neutral"):
        req = SearchRequest(query="test", sentiment=label)
        assert req.sentiment == label


def test_search_request_invalid_sentiment_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(query="test", sentiment="positive")  # lowercase rejected


def test_search_request_source_too_long_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(query="test", source="x" * 65)


# ── ScrapeCommand validation ──────────────────────────────────────────────────

def test_scrape_command_valid():
    cmd = ScrapeCommand(source="TRT Haber")
    assert cmd.source == "TRT Haber"


def test_scrape_command_empty_source_rejected():
    with pytest.raises(ValidationError):
        ScrapeCommand(source="")


def test_scrape_command_source_too_long_rejected():
    with pytest.raises(ValidationError):
        ScrapeCommand(source="x" * 65)


def test_scrape_command_source_max_length_accepted():
    cmd = ScrapeCommand(source="x" * 64)
    assert len(cmd.source) == 64
