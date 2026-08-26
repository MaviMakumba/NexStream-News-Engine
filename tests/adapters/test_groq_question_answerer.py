import pytest
from unittest.mock import patch, MagicMock
from src.adapters.analysis.groq_question_answerer import GroqQuestionAnswerer
from src.domain.ports.question_answering_port import QuestionAnsweringError


def make_mock_response(content: str, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {"choices": [{"message": {"content": content}}]}
    mock.raise_for_status = MagicMock()
    return mock


def _sources():
    return [{"index": 1, "title": "Başlık", "source": "BBC", "sentiment_label": "Neutral",
             "corroboration_count": 1, "published_at": "2026-08-20"}]


def test_answer_returns_parsed_result():
    qa = GroqQuestionAnswerer()
    response_json = '{"coverage": "full", "answer": "Cevap.", "used_sources": [1]}'
    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = qa.answer("Ne oldu?", _sources(), [], "single_source")
    assert result["coverage"] == "full"
    assert result["answer"] == "Cevap."
    assert result["used_sources"] == [1]


def test_answer_retries_on_rate_limit():
    qa = GroqQuestionAnswerer()
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"retry-after": "1"}
    rate_limit_response.raise_for_status = MagicMock()
    success = make_mock_response('{"coverage": "full", "answer": "OK", "used_sources": [1]}')
    with patch("requests.post", side_effect=[rate_limit_response, success]), patch("time.sleep"):
        result = qa.answer("Ne oldu?", _sources(), [], "single_source")
    assert result["coverage"] == "full"


def test_answer_raises_after_exhausting_json_parse_errors():
    qa = GroqQuestionAnswerer()
    bad_response = make_mock_response("Bu JSON değil.")
    with patch("requests.post", return_value=bad_response):
        with pytest.raises(QuestionAnsweringError):
            qa.answer("Ne oldu?", _sources(), [], "single_source")


def test_answer_raises_on_connection_error():
    """AnalysisPort'un aksine bu port'ta sessiz nötr fallback YOK — spec 'Amaç'
    bölümü: 'kibarca uydurulmuş' bir cevap vermek açık hatadan daha kötü."""
    qa = GroqQuestionAnswerer()
    with patch("requests.post", side_effect=Exception("Connection refused")), \
         patch("src.adapters.analysis.groq_question_answerer.time.sleep"):
        with pytest.raises(QuestionAnsweringError):
            qa.answer("Ne oldu?", _sources(), [], "single_source")


def test_answer_passes_corroboration_level_into_prompt():
    qa = GroqQuestionAnswerer()
    response_json = '{"coverage": "full", "answer": "OK", "used_sources": [1]}'
    captured = {}

    def capture(*args, **kwargs):
        captured["prompt"] = kwargs["json"]["messages"][0]["content"]
        return make_mock_response(response_json)

    with patch("requests.post", side_effect=capture):
        qa.answer("Ne oldu?", _sources(), [], "multi_source")
    assert "multiple" in captured["prompt"].lower()


# ── factory ──────────────────────────────────────────────────────────────

def test_build_question_answerer_returns_groq_adapter():
    from src.adapters.analysis.factory import build_question_answerer
    assert isinstance(build_question_answerer(), GroqQuestionAnswerer)
