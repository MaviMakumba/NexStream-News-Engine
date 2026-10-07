"""Cevaptaki özel isimleri kanıttaki yazımla doğrular (RAG, 7 Eki 2026 canlı bulgu).

Model, kanıtta doğru yazılmış bir ismi bozabiliyor (Osimhen → "Osimren"/"Osimiren"). Burada
kanıtta AYNEN geçmeyen ama kanıttaki büyük harfli bir kelimenin 1-2 harf farkıyla yazılmış
hâli olan isimler kanıttaki yazıma çevrilir. Yanlış düzeltme eksik düzeltmeden kötüdür; bu
yüzden her belirsizlikte (kısa kelime, soruda geçen yazım, eşit uzaklıkta birden çok aday,
kanıtta küçük harfle geçen sıradan kelime) metne DOKUNULMAZ.

Saf fonksiyon: dış bağımlılık yok. Yalnız yazım hatasını yakalar; modelin tamamen farklı bir
isim uydurmasını (Icardi yerine Mertens) yakalamaz.
"""

import re
from typing import Sequence

MIN_NAME_LENGTH = 5
_CAPITALIZED = re.compile(r"(?<!\w)([A-ZÇĞİÖŞÜ]\w{%d,})" % (MIN_NAME_LENGTH - 1))
_WORD = re.compile(r"\w+")


def _fold(word: str) -> str:
    """Türkçe-duyarlı küçük harf: İ→i, I→ı (str.lower() 'İ'yi birleşik noktalı i'ye çevirir)."""
    return word.replace("İ", "i").replace("I", "ı").lower()


def _max_distance(length: int) -> int:
    return 1 if length <= 7 else 2


def _distance(a: str, b: str) -> int:
    """Optimal string alignment (Damerau) uzaklığı: ekleme, silme, değiştirme, bitişik yer değiştirme."""
    rows = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        rows[i][0] = i
    for j in range(len(b) + 1):
        rows[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            rows[i][j] = min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[len(a)][len(b)]


def correct_names(answer: str, evidence_texts: Sequence[str], question: str) -> tuple[str, list[tuple[str, str]]]:
    """(düzeltilmiş cevap, [(eski, yeni), ...]) döner."""
    if not answer or not evidence_texts:
        return answer, []

    reference_words = [w for text in (*evidence_texts, question) for w in _WORD.findall(text)]
    known_folded = {_fold(w) for w in reference_words}
    # Kanıtta küçük harfle geçen kelime sıradan bir kelimedir (cümle başındaki "Ancak" gibi).
    common_lowercase = {_fold(w) for w in reference_words if w == w.lower()}
    candidates = {w for text in evidence_texts for w in _CAPITALIZED.findall(text)}

    replacements: dict[str, str] = {}
    for word in dict.fromkeys(_CAPITALIZED.findall(answer)):
        folded = _fold(word)
        if folded in known_folded or folded in common_lowercase:
            continue
        limit = _max_distance(len(word))
        scored = {}
        for candidate in candidates:
            if abs(len(candidate) - len(word)) > limit:
                continue
            distance = _distance(folded, _fold(candidate))
            if distance <= limit:
                scored[candidate] = distance
        if not scored:
            continue
        best = min(scored.values())
        nearest = [c for c, d in scored.items() if d == best]
        if len(nearest) == 1:
            replacements[word] = nearest[0]

    if not replacements:
        return answer, []
    corrected = _CAPITALIZED.sub(lambda m: replacements.get(m.group(1), m.group(1)), answer)
    return corrected, list(replacements.items())
