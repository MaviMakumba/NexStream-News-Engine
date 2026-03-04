from src.adapters.analysis.textblob_analyzer import TextBlobAnalyzer

def test_positive_text():
    """Pozitif metin doğru etiketleniyor mu?"""
    analyzer = TextBlobAnalyzer()
    result = analyzer.analyze_text("This is wonderful and amazing news!")
    assert result["sentiment_label"] == "Positive"
    assert result["sentiment_score"] > 0.1

def test_negative_text():
    """Negatif metin doğru etiketleniyor mu?"""
    analyzer = TextBlobAnalyzer()
    result = analyzer.analyze_text("This is terrible and awful news.")
    assert result["sentiment_label"] == "Negative"
    assert result["sentiment_score"] < -0.1

def test_empty_text():
    """Boş metin hata vermemeli"""
    analyzer = TextBlobAnalyzer()
    result = analyzer.analyze_text("")
    assert result["sentiment_label"] == "Neutral"
    assert result["sentiment_score"] == 0.0
    assert result["summary"] == "No Content"

def test_result_has_required_keys():
    """Sonuç her zaman 3 alan içermeli"""
    analyzer = TextBlobAnalyzer()
    result = analyzer.analyze_text("Some news text here.")
    assert "sentiment_score" in result
    assert "sentiment_label" in result
    assert "summary" in result

def test_summary_is_first_two_sentences():
    """Özet ilk 2 cümleyi alıyor mu?"""
    analyzer = TextBlobAnalyzer()
    text = "First sentence. Second sentence. Third sentence."
    result = analyzer.analyze_text(text)
    assert "Third sentence" not in result["summary"]