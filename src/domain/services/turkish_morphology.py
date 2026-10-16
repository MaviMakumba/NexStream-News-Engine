"""Pragmatik Türkçe çekim eki tanıma — gerçek morfolojik analiz DEĞİL.

Anahtar kelime eşleştirmesi "kelimenin BAŞINDA" arar ki çekimleri yakalasın
("tren" → "trenin", "trenler", "trende"). Ama saf önek eşleşmesi kökle
BAŞLAYAN her kelimeyi de yakalar: "tren" → "Trendyol", "trend" (29 Eylül 2026'da
canlı bülten e-postasında bulundu: HT Spor'un "Trendyol Süper Lig" haberi "tren"
anahtar kelimesiyle eşleşti). Çözüm: kökten sonra kalan parça BOŞ ya da geçerli
bir çekim-eki DİZİSİ olmalı; "dyol", "d" gibi artıklar çekim eki değildir.

Ek listesi `news_service._stem_tr` tarafından da kullanılır (tek doğruluk kaynağı,
application → domain bağımlılık yönü korunur).
"""

from functools import lru_cache
from typing import Tuple

# İsim çekim ekleri, en uzun önce (kök kırpma `_stem_tr`'nin sırasına bağlı).
TR_NOMINAL_SUFFIXES: Tuple[str, ...] = (
    "larından", "lerinden",
    "lardan", "lerden", "larla", "lerle",
    "larda", "lerde", "lara", "lere", "ların", "lerin",
    "ından", "inden", "undan", "ünden",
    "ları", "leri",
    "ndan", "nden", "ında", "inde", "unda", "ünde",
    "lar", "ler",
    "nda", "nde", "nın", "nin", "nun", "nün",
    "ına", "ine", "una", "üne",
    "ını", "ini", "unu", "ünü",
    "dan", "den", "tan", "ten",
    "yla", "yle",
    "nı", "ni", "nu", "nü",
    "na", "ne",
    "ya", "ye", "yı", "yi", "yu", "yü",
    "da", "de", "ta", "te",
    "la", "le",
    "li", "lı", "lu", "lü",
    "sı", "si", "su", "sü",
    "ın", "in", "un", "ün",
    "ı", "i", "u", "ü",
)

# SADECE eşleştirmede geçerli ek olarak kabul edilen ilaveler (kök kırpmada kullanılmaz:
# `_stem_tr`'yi agresifleştirmemek için): iyelik (-imiz/-iniz), aitlik (-ki), ek-fiil
# (-dir), ölçü/pekiştirme ve İngilizce çoğul (-s/-es: kaynakların yarısı İngilizce).
_MATCH_ONLY_SUFFIXES: Tuple[str, ...] = (
    "imiz", "ımız", "umuz", "ümüz", "iniz", "ınız", "unuz", "ünüz",
    "im", "ım", "um", "üm",
    "ki", "dir", "dır", "dur", "dür", "tir", "tır", "tur", "tür",
    "ce", "ca", "çe", "ça", "cik", "cık",
    "yi", "yı", "yu", "yü",
    "a", "e",                              # yönelme: ünsüzle biten kök + -a/-e ("trene", "borsaya"nın kardeşi)
    "siz", "sız", "suz", "süz",
    "spor",                                # şehir + spor kulübü: Kocaelispor, Sakaryaspor, Bursaspor (her şehir için ayrı kural yazılmaz)
    "s", "es",
)

_ALL_SUFFIXES: Tuple[str, ...] = tuple(sorted(set(TR_NOMINAL_SUFFIXES) | set(_MATCH_ONLY_SUFFIXES),
                                              key=len, reverse=True))
_MAX_CHAIN = 5   # "trenlerimizdekiler" gibi gerçekçi zincirler ≤ 4-5 ek


@lru_cache(maxsize=4096)
def _is_suffix_chain(rest: str, depth: int = _MAX_CHAIN) -> bool:
    if rest == "":
        return True
    if depth == 0:
        return False
    for suffix in _ALL_SUFFIXES:
        if rest.startswith(suffix) and _is_suffix_chain(rest[len(suffix):], depth - 1):
            return True
    return False


# Soru çerçevesi kökleri: konu bilgisi taşımayan, cümleyi soruya çeviren kapalı sınıf.
# "kim"/"ne" BİLİNÇLİ yok: ek zincirleriyle "kimya"/"nete" gibi gerçek kelimeleri yutarlardı
# (bu ikisi news_service'te literal soru parçacığı olarak ayrıca elenir).
_QUESTION_ROOTS: Tuple[str, ...] = ("kaç", "hangi", "nere", "nasıl", "neden", "niçin", "niye")
# Sıra sayısı eki: "kaç" + "ıncı" = "kaçıncı" (ek zincirinde olmayan, soruya özgü bir yapı).
_ORDINAL_SUFFIXES: Tuple[str, ...] = ("ıncı", "inci", "uncu", "üncü")


def is_question_word(word: str) -> bool:
    """`word` ("kaçıncı", "kaçta", "hangisi", "nerede") bir soru çerçevesi sözcüğü mü?

    Kelime listesi değil dilbilgisi sınıfı: soru kökü + geçerli çekim eki dizisi (ya da
    sıra eki). "kaçak"/"kaçırıldı" gibi içerik kelimelerinde kalan parça çekim eki
    olmadığı için False döner. Ön koşul: Türkçe-uyumlu küçük harf.
    """
    for root in _QUESTION_ROOTS:
        if is_inflection_of(root, word):
            return True
    return any(word == "kaç" + suffix for suffix in _ORDINAL_SUFFIXES)


def is_inflection_of(term: str, word: str) -> bool:
    """`word`, `term` kökünün olası bir çekimi (ya da kendisi) mi?

    Ön koşul: ikisi de Türkçe-uyumlu küçük harfe çevrilmiş. "tren" için "trenler",
    "trenin", "trende" True; "trendyol", "trend", "trenyolu" False.
    """
    if not word.startswith(term):
        return False
    return _is_suffix_chain(word[len(term):])
