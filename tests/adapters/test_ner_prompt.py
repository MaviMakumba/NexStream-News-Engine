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
    from src.domain.topics import TOPICS
    valid_topics = [t.id for t in TOPICS]
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


def test_sentiment_label_derived_from_score_not_model_text():
    """28-29 Eyl 2026: qwen bir haber için 'Strongly Negative' üretti (UI/filtre yalnızca
    Positive|Negative|Neutral biliyor). Etiket skorun saf fonksiyonu: >0.2 / <-0.2 / arası."""
    import json
    from src.adapters.analysis.common import parse_analysis_json

    def label(score, model_label):
        raw = json.dumps({"sentiment_score": score, "sentiment_label": model_label,
                          "summary": "s", "entities": {}, "topic": "World"})
        return parse_analysis_json(raw, "text")["sentiment_label"]

    assert label(-0.9, "Strongly Negative") == "Negative"
    assert label(0.85, "Very Positive") == "Positive"
    assert label(0.0, "Mixed") == "Neutral"
    assert label(0.2, "Positive") == "Neutral"      # sınır: >0.2 değil
    assert label(-0.2, "Negative") == "Neutral"     # sınır: <-0.2 değil
    assert label(0.21, "Neutral") == "Positive"
    assert label(-0.21, "Neutral") == "Negative"
def test_model_invented_topic_variants_fall_back_to_other():
    """'Finance', küçük harf 'crypto', boş ya da sayı → 'Other' (çökme yok)."""
    import json as _json
    from src.adapters.analysis.common import parse_analysis_json
    for bad in ("Finance", "crypto", "", None, 7):
        raw = _json.dumps({"sentiment_score": 0.0, "summary": "s", "entities": {}, "topic": bad})
        assert parse_analysis_json(raw, "t")["topic"] == "Other", repr(bad)
