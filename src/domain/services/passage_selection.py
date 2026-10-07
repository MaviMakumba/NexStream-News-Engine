"""Saf pasaj seçimi — makale metninden soruya en alakalı paragrafları token bütçesi içinde seçer.

Embedding çağrısı burada YOK (domain dış bağımlılık bilmez): vektörler dışarıdan gelir,
`EvidenceEnricher` `EmbeddingPort` ile üretir.
"""

import math
import re
from typing import Sequence

MIN_PARAGRAPH_CHARS = 40
MAX_PARAGRAPH_CHARS = 600
MAX_PARAGRAPHS = 60
# Türkçe için muhafazakâr (gerçek oran ~3.5-4 karakter/token): bütçeyi aşmaktansa az doldurmak.
CHARS_PER_TOKEN = 3


def estimate_tokens(text: str) -> int:
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def split_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for raw in re.split(r"\n+", text):
        paragraph = " ".join(raw.split())
        if len(paragraph) < MIN_PARAGRAPH_CHARS:
            continue
        paragraphs.append(paragraph[:MAX_PARAGRAPH_CHARS])
        if len(paragraphs) >= MAX_PARAGRAPHS:
            break
    return paragraphs


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)


def select_passages(
    paragraphs: Sequence[str],
    question_vector: Sequence[float],
    paragraph_vectors: Sequence[Sequence[float]],
    token_budget: int,
) -> list[str]:
    """Soruya en benzer paragrafları açgözlü seçer; sığmayanı atlayıp aramaya devam eder.
    Hiçbiri sığmazsa en iyisi bütçeye kırpılır. Dönüş özgün metin sırasındadır."""
    if len(paragraphs) != len(paragraph_vectors):
        raise ValueError("paragraphs ve paragraph_vectors aynı uzunlukta olmalı")
    if not paragraphs:
        return []
    ranked = sorted(
        range(len(paragraphs)),
        key=lambda i: cosine_similarity(question_vector, paragraph_vectors[i]),
        reverse=True,
    )
    chosen: list[int] = []
    used = 0
    for i in ranked:
        cost = estimate_tokens(paragraphs[i])
        if used + cost > token_budget:
            continue
        chosen.append(i)
        used += cost
    if not chosen:
        return [paragraphs[ranked[0]][: token_budget * CHARS_PER_TOKEN]]
    return [paragraphs[i] for i in sorted(chosen)]
