import json
import pytest
from src.adapters.analysis.rag_common import build_rag_prompt, parse_rag_json

_TODAY = "2026-08-31"


def _source(index=1, title="Test Başlık", source="BBC", sentiment_label="Neutral",
            corroboration_count=1, published_at="2026-08-20", content="Test içerik metni."):
    return {"index": index, "title": title, "source": source, "sentiment_label": sentiment_label,
            "corroboration_count": corroboration_count, "published_at": published_at, "content": content}


def test_build_rag_prompt_includes_numbered_evidence():
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "single_source", today=_TODAY)
    assert "[1]" in prompt
    assert "Test Başlık" in prompt
    assert "BBC" in prompt


def test_build_rag_prompt_includes_question():
    prompt = build_rag_prompt("Beşiktaş ne yaptı?", [_source()], [], "single_source", today=_TODAY)
    assert "Beşiktaş ne yaptı?" in prompt


def test_build_rag_prompt_includes_history():
    history = [{"role": "user", "content": "İstanbul'da ne oldu?"}]
    prompt = build_rag_prompt("Peki ya İzmir'de?", [_source()], history, "single_source", today=_TODAY)
    assert "İstanbul'da ne oldu?" in prompt


def test_build_rag_prompt_includes_evidence_content():
    """Kanıt sadece başlık değil, elimizde olan content'i de içermeli — LLM
    başlıkta olmayan ama teaser'da geçen detayları (27 Ağu 2026 canlı
    bulgusu) görebilsin."""
    prompt = build_rag_prompt("Ne oldu?", [_source(content="Trossard kafilede yer almadı.")], [], "single_source", today=_TODAY)
    assert "Trossard kafilede yer almadı." in prompt


def test_build_rag_prompt_notes_multi_source_corroboration():
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "multi_source", today=_TODAY)
    assert "multiple" in prompt.lower()


def test_build_rag_prompt_notes_single_source_caveat():
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "single_source", today=_TODAY)
    assert "single source" in prompt.lower()


# ── Tarih-farkındalığı (31 Ağu 2026, kullanıcı bulgusu: eski habere göre cevap veriliyordu) ──

def test_build_rag_prompt_includes_todays_date():
    """Model 'bugün'ü bilmeden bir kanıtın ne kadar eski olduğunu anlayamaz."""
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "single_source", today=_TODAY)
    assert _TODAY in prompt


def test_build_rag_prompt_instructs_to_prefer_latest_evidence_on_conflict():
    """Aynı konuda birden fazla tarihli kanıt varsa modele en yeniyi esas
    alması açıkça söylenmeli — sadece tarihi göstermek yetmiyordu (model
    hangisine öncelik vereceğini bilmiyordu, 31 Ağu 2026 kullanıcı bulgusu)."""
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "single_source", today=_TODAY)
    assert "most recent" in prompt.lower() or "latest" in prompt.lower()


def test_parse_rag_json_valid_response():
    content = '{"coverage": "full", "answer": "Cevap metni.", "used_sources": [1, 2]}'
    result = parse_rag_json(content)
    assert result == {"coverage": "full", "answer": "Cevap metni.", "used_sources": [1, 2]}


def test_parse_rag_json_strips_markdown_fences():
    content = '```json\n{"coverage": "partial", "answer": "X", "used_sources": [1]}\n```'
    result = parse_rag_json(content)
    assert result["coverage"] == "partial"


def test_parse_rag_json_invalid_coverage_falls_back_to_none():
    content = '{"coverage": "maybe", "answer": "X", "used_sources": []}'
    result = parse_rag_json(content)
    assert result["coverage"] == "none"


def test_parse_rag_json_non_list_used_sources_becomes_empty():
    content = '{"coverage": "full", "answer": "X", "used_sources": "oops"}'
    result = parse_rag_json(content)
    assert result["used_sources"] == []


def test_parse_rag_json_non_int_elements_filtered_out():
    content = '{"coverage": "full", "answer": "X", "used_sources": [1, "2", 3]}'
    result = parse_rag_json(content)
    assert result["used_sources"] == [1, 3]


def test_parse_rag_json_missing_fields_use_safe_defaults():
    content = '{}'
    result = parse_rag_json(content)
    assert result == {"coverage": "none", "answer": "", "used_sources": []}


def test_parse_rag_json_non_string_answer_becomes_empty():
    content = '{"coverage": "full", "answer": 42, "used_sources": []}'
    result = parse_rag_json(content)
    assert result["answer"] == ""


def test_parse_rag_json_raises_on_completely_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        parse_rag_json("Bu JSON değil, düz metin.")
