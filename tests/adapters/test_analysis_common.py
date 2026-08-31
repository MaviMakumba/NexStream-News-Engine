"""build_analysis_prompt sözleşme + boyut regresyon testleri.

31 Ağu 2026 (roadmap #25): şablon metni TPD maliyetini düşürmek için
sıkıştırıldı. Bu test iki şeyi garanti eder: (1) sıkıştırma alan sözleşmesini
bozmadı — GroqAnalyzer/HuggingFaceAnalyzer'ın parse_analysis_json'a
beklediği her alan hâlâ prompt'ta açıkça isteniyor, (2) şablon tekrar
şişmesin diye sabit bir karakter bütçesi altında kalıyor (makale
içeriğinden bağımsız kısım — [:1000] kırpması olmadan ölçülür).
"""
from src.adapters.analysis.common import build_analysis_prompt

# Şablonun kendisi (makale metni olmadan) — bu, her Groq çağrısında tekrarlanan
# sabit ek yük. 850 karakter (~212 token) sıkıştırma öncesi ~1113 karakterdi
# (~278 token); yeniden şişmeye karşı regresyon tavanı olarak biraz payla tutuldu.
_TEMPLATE_ONLY_CHAR_BUDGET = 850


def test_template_only_overhead_stays_under_budget():
    """Makale metninden bağımsız sabit şablon ek yükü bütçeyi aşmamalı."""
    template_only = build_analysis_prompt("")
    assert len(template_only) < _TEMPLATE_ONLY_CHAR_BUDGET


def test_prompt_requests_every_required_field():
    prompt = build_analysis_prompt("Örnek haber metni.")
    for field in ("sentiment_score", "sentiment_label", "summary", "entities", "topic"):
        assert field in prompt


def test_prompt_still_calibrates_sentiment_extremes():
    """Sıkıştırma, uç değer kalibrasyon örneklerini (breakthrough/victory,
    disaster/death/crisis) silmemeli — bunlar modelin skor aralığını
    doğru kullanmasını sağlıyor, sadece madde işaretleri/tekrar kırpıldı."""
    prompt = build_analysis_prompt("")
    assert "breakthrough" in prompt or "victory" in prompt
    assert "disaster" in prompt or "crisis" in prompt


def test_prompt_truncates_article_at_1000_chars():
    long_text = "A" * 2000
    prompt = build_analysis_prompt(long_text)
    assert "A" * 1001 not in prompt
    assert "A" * 1000 in prompt
