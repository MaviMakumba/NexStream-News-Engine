import pytest
from unittest.mock import patch, MagicMock
from src.adapters.analysis.groq_analyzer import GroqAnalyzer


def make_mock_response(content: str, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock.raise_for_status = MagicMock()
    return mock


FULL_RESPONSE = (
    '{"sentiment_score": 0.6, "sentiment_label": "Positive", "summary": "Tech event.",'
    ' "entities": {"persons": ["Elon Musk"], "organizations": ["Tesla", "SpaceX"], "locations": ["California"]},'
    ' "topic": "Technology"}'
)


def test_analyze_returns_entities():
    analyzer = GroqAnalyzer()
    with patch("requests.post", return_value=make_mock_response(FULL_RESPONSE)):
        result = analyzer.analyze_text("Elon Musk announced Tesla expansion in California.")

    assert "entities" in result
    assert result["entities"]["persons"] == ["Elon Musk"]
    assert "Tesla" in result["entities"]["organizations"]
    assert result["entities"]["locations"] == ["California"]


def test_analyze_returns_topic():
    analyzer = GroqAnalyzer()
    with patch("requests.post", return_value=make_mock_response(FULL_RESPONSE)):
        result = analyzer.analyze_text("Tech news.")

    assert result["topic"] == "Technology"


def test_entities_default_when_missing():
    analyzer = GroqAnalyzer()
    response = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "News."}'
    with patch("requests.post", return_value=make_mock_response(response)):
        result = analyzer.analyze_text("Some news.")

    assert result["entities"] == {"persons": [], "organizations": [], "locations": []}


def test_topic_defaults_to_other_when_missing():
    analyzer = GroqAnalyzer()
    response = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "News."}'
    with patch("requests.post", return_value=make_mock_response(response)):
        result = analyzer.analyze_text("Some news.")

    assert result["topic"] == "Other"


def test_invalid_topic_normalized_to_other():
    analyzer = GroqAnalyzer()
    response = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "News.", "entities": {}, "topic": "InvalidCategory"}'
    with patch("requests.post", return_value=make_mock_response(response)):
        result = analyzer.analyze_text("Some news.")

    assert result["topic"] == "Other"


def test_entities_invalid_type_normalized():
    analyzer = GroqAnalyzer()
    response = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "News.", "entities": "not a dict", "topic": "Sports"}'
    with patch("requests.post", return_value=make_mock_response(response)):
        result = analyzer.analyze_text("Some news.")

    assert result["entities"] == {"persons": [], "organizations": [], "locations": []}


def test_entities_partial_keys_filled():
    analyzer = GroqAnalyzer()
    response = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "News.", "entities": {"persons": ["Ali"]}, "topic": "Other"}'
    with patch("requests.post", return_value=make_mock_response(response)):
        result = analyzer.analyze_text("Some news.")

    assert result["entities"]["persons"] == ["Ali"]
    assert result["entities"]["organizations"] == []
    assert result["entities"]["locations"] == []


def test_fallback_includes_entities_and_topic():
    analyzer = GroqAnalyzer()
    # time.sleep patch'i ŞART — bkz. test_groq_analyzer.py'deki aynı desen:
    # hata yolundaki iki `time.sleep(5)` bu testi 10 saniye bekletiyordu.
    with patch("requests.post", side_effect=Exception("Connection refused")), \
         patch("src.adapters.analysis.groq_analyzer.time.sleep"):
        result = analyzer.analyze_text("Some news.")

    assert result["entities"] == {"persons": [], "organizations": [], "locations": []}
    assert result["topic"] == "Other"


def test_all_valid_topics_accepted():
    analyzer = GroqAnalyzer()
    valid_topics = ["Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World", "Other"]
    for topic in valid_topics:
        response = f'{{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "N.", "entities": {{}}, "topic": "{topic}"}}'
        with patch("requests.post", return_value=make_mock_response(response)):
            result = analyzer.analyze_text("Test.")
        assert result["topic"] == topic


def test_prompt_contains_entity_instruction():
    analyzer = GroqAnalyzer()
    captured = {}

    def capture(*args, **kwargs):
        captured["json"] = kwargs.get("json", {})
        return make_mock_response(FULL_RESPONSE)

    with patch("requests.post", side_effect=capture):
        analyzer.analyze_text("Test text.")

    prompt = captured["json"]["messages"][0]["content"]
    assert "entities" in prompt
    assert "persons" in prompt
    assert "organizations" in prompt
    assert "locations" in prompt
    assert "topic" in prompt
