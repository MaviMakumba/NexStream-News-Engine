import pytest
from unittest.mock import patch, MagicMock
from src.adapters.analysis.groq_analyzer import GroqAnalyzer


def make_mock_response(content: str, status_code: int = 200, headers: dict = None):
    """Groq API'sinin başarılı yanıtını taklit eder."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.headers = headers if headers is not None else {}
    mock.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock.raise_for_status = MagicMock()
    return mock


def make_error_response(status_code: int):
    """HTTP hata yanıtını taklit eder."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status.side_effect = Exception(f"{status_code} Error")
    return mock


# ── Başarılı Senaryolar ───────────────────────────────────────────────────────

def test_positive_sentiment():
    """Pozitif haber doğru etiket ve pozitif skor döndürür."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.85, "sentiment_label": "Positive", "summary": "Great news."}'

    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = analyzer.analyze_text("Apple stock hits record high today!")

    assert result["sentiment_label"] == "Positive"
    assert result["sentiment_score"] == 0.85
    assert "summary" in result


def test_negative_sentiment():
    """Negatif haber doğru etiket ve negatif skor döndürür."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": -0.90, "sentiment_label": "Negative", "summary": "Tragic event."}'

    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = analyzer.analyze_text("Major earthquake kills hundreds.")

    assert result["sentiment_label"] == "Negative"
    assert result["sentiment_score"] == -0.90


def test_neutral_sentiment():
    """Nötr haber doğru etiket ve sıfıra yakın skor döndürür."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "Weather update."}'

    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = analyzer.analyze_text("The weather today is partly cloudy.")

    assert result["sentiment_label"] == "Neutral"
    assert result["sentiment_score"] == 0.0


def test_result_has_required_keys():
    """Dönen dict her zaman 3 zorunlu anahtarı içerir."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.5, "sentiment_label": "Positive", "summary": "Test summary."}'

    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = analyzer.analyze_text("Some news text.")

    assert "sentiment_score" in result
    assert "sentiment_label" in result
    assert "summary" in result


def test_score_is_float():
    """sentiment_score her zaman float döner."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 1, "sentiment_label": "Positive", "summary": "Test."}'

    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = analyzer.analyze_text("Amazing news!")

    assert isinstance(result["sentiment_score"], float)


def test_strips_markdown_fences():
    """Model yanıtında markdown backtick bloğu varsa temizler."""
    analyzer = GroqAnalyzer()
    response_with_fences = '```json\n{"sentiment_score": 0.7, "sentiment_label": "Positive", "summary": "Good news."}\n```'

    with patch("requests.post", return_value=make_mock_response(response_with_fences)):
        result = analyzer.analyze_text("Good news today.")

    assert result["sentiment_label"] == "Positive"
    assert result["sentiment_score"] == 0.7


def test_turkish_text_analyzed():
    """Türkçe metin de başarıyla analiz edilir."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.8, "sentiment_label": "Positive", "summary": "Besiktas won the championship."}'

    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = analyzer.analyze_text("Beşiktaş şampiyonluk kupasını kaldırdı!")

    assert result["sentiment_label"] == "Positive"
    assert isinstance(result["summary"], str)


# ── Hata Senaryoları ──────────────────────────────────────────────────────────

def test_returns_neutral_on_json_parse_error():
    """Model geçersiz JSON döndürürse fallback Neutral döner."""
    analyzer = GroqAnalyzer()
    bad_response = "Bu JSON değil, düz metin."

    with patch("requests.post", return_value=make_mock_response(bad_response)):
        result = analyzer.analyze_text("Some news.")

    assert result["sentiment_label"] == "Neutral"
    assert result["sentiment_score"] == 0.0


def test_returns_neutral_on_connection_error():
    """Bağlantı hatası durumunda fallback Neutral döner, exception fırlatmaz."""
    analyzer = GroqAnalyzer()

    # time.sleep patch'i ŞART: hata yolunda iki kez `time.sleep(5)` var, yani
    # bu test gerçekten 10 saniye bekliyordu. Beklemeyi test etmiyoruz,
    # fallback davranışını test ediyoruz.
    with patch("requests.post", side_effect=Exception("Connection refused")), \
         patch("src.adapters.analysis.groq_analyzer.time.sleep"):
        result = analyzer.analyze_text("Some news.")

    assert result["sentiment_label"] == "Neutral"
    assert result["sentiment_score"] == 0.0


def test_retries_on_rate_limit():
    """429 Rate limit hatası alınca retry yapar."""
    analyzer = GroqAnalyzer()
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.raise_for_status = MagicMock()

    success_json = '{"sentiment_score": 0.5, "sentiment_label": "Positive", "summary": "Good."}'
    success_response = make_mock_response(success_json)

    with patch("requests.post", side_effect=[rate_limit_response, success_response]):
        with patch("time.sleep"):  # sleep'i atla, test hızlı çalışsın
            result = analyzer.analyze_text("Some news.")

    assert result["sentiment_label"] == "Positive"


def test_text_truncated_to_1000_chars():
    """1000 karakterden uzun metinler prompt'ta kısaltılır."""
    analyzer = GroqAnalyzer()
    long_text = "A" * 5000
    response_json = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "Long text."}'

    captured_payload = {}

    def capture_request(*args, **kwargs):
        captured_payload["json"] = kwargs.get("json", {})
        return make_mock_response(response_json)

    with patch("requests.post", side_effect=capture_request):
        analyzer.analyze_text(long_text)

    prompt = captured_payload["json"]["messages"][0]["content"]
    # 1000 karakterden fazla A bloğu prompt'ta olmamalı
    assert "A" * 1001 not in prompt


# ── TPM Proaktif Throttle (Groq TPM=8000, RPM=30 throttle'ı hiç hesaba katmıyordu) ──

def test_proactively_waits_when_tpm_budget_nearly_exhausted():
    """Groq'un döndürdüğü kalan token bütçesi güvenlik payının altındaysa,
    429'u BEKLEMEDEN, Groq'un bildirdiği reset süresi kadar proaktif bekler."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "OK."}'
    headers = {"x-ratelimit-remaining-tokens": "300", "x-ratelimit-reset-tokens": "7.66s"}

    with patch("requests.post", return_value=make_mock_response(response_json, headers=headers)), \
         patch("src.adapters.analysis.groq_analyzer.time.sleep") as mock_sleep:
        analyzer.analyze_text("Some news.")

    mock_sleep.assert_called_once_with(7.66)


def test_does_not_wait_when_tpm_budget_healthy():
    """Kalan token bütçesi güvenlik payının üzerindeyse ekstra bekleme yapılmaz."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "OK."}'
    headers = {"x-ratelimit-remaining-tokens": "7500", "x-ratelimit-reset-tokens": "0.5s"}

    with patch("requests.post", return_value=make_mock_response(response_json, headers=headers)), \
         patch("src.adapters.analysis.groq_analyzer.time.sleep") as mock_sleep:
        analyzer.analyze_text("Some news.")

    mock_sleep.assert_not_called()


def test_missing_ratelimit_headers_does_not_crash():
    """Header'lar hiç dönmezse (eski/farklı davranış) sessizce atlanır, sonuç yine döner."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": "OK."}'

    with patch("requests.post", return_value=make_mock_response(response_json, headers={})), \
         patch("src.adapters.analysis.groq_analyzer.time.sleep") as mock_sleep:
        result = analyzer.analyze_text("Some news.")

    assert result["sentiment_label"] == "Neutral"
    mock_sleep.assert_not_called()


def test_parses_minutes_and_seconds_duration():
    """Groq'un '2m59.56s' süre formatı doğru saniyeye çevrilir."""
    assert GroqAnalyzer._parse_duration("2m59.56s") == pytest.approx(179.56)


def test_parses_seconds_only_duration():
    """Groq'un '7.66s' süre formatı doğru saniyeye çevrilir."""
    assert GroqAnalyzer._parse_duration("7.66s") == pytest.approx(7.66)


def test_parses_empty_duration_as_zero():
    """Boş/eksik süre string'i çökme yerine 0 döner."""
    assert GroqAnalyzer._parse_duration("") == 0.0


def test_non_dict_like_headers_does_not_crash():
    """headers gerçek bir dict değilse (ör. .get() de mock'lanmış bir MagicMock
    döndürüyorsa — test_ner_prompt.py'nin sade mock'u gibi), proaktif throttle
    sessizce atlanır, analiz sonucu yine döner."""
    analyzer = GroqAnalyzer()
    response_json = '{"sentiment_score": 0.5, "sentiment_label": "Positive", "summary": "OK."}'
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": response_json}}]}
    mock_response.raise_for_status = MagicMock()
    # mock_response.headers'a hiç dokunulmadı — çıplak MagicMock, .get() de
    # gerçek string değil MagicMock döndürür.

    with patch("requests.post", return_value=mock_response), \
         patch("src.adapters.analysis.groq_analyzer.time.sleep") as mock_sleep:
        result = analyzer.analyze_text("Some news.")

    assert result["sentiment_label"] == "Positive"
    mock_sleep.assert_not_called()