"""Bir haberin bir abonenin tercihleriyle eşleşip eşleşmediğini belirleyen saf
domain mantığı — dış bağımlılık yok (bkz. domain/scoring/ ile aynı felsefe).

Hem anlık keyword alert'te (news_service.py) hem günlük digest
kişiselleştirmesinde (newsletter_job.py) kullanılır — eskiden ikisi de kendi
keyword eşleştirme mantığını ayrı ayrı yazıyordu.
"""

import re
from typing import Dict, FrozenSet, List, Optional
from src.domain.models.article import Article
from src.domain.models.subscriber import Subscriber

# Bilinen "yanlış dost" (false friend) çakışmaları: bir kök harf düzeyinde
# BAŞKA, dilbilgisel olarak alakasız bir kelimenin çekimli haliyle çakışıyorsa
# (ör. "altın" [gold] kökü, "alt" [under] kelimesinin "altı"+buffer "n"+"da/daki"
# çekimiyle üretilen "altında"/"altındaki" ile TAM AYNI harfleri paylaşıyor).
# \b-anchor tek başına bunu ayıklayamaz çünkü çakışan kelimenin önünde GERÇEK
# bir kelime sınırı var (gözaltı bug'ından farkı — orada sınır yoktu). Gerçek
# morfolojik analiz olmadan bu ayrım yapılamaz (bkz. `_stem_tr` benzeri
# "pragmatik, gerçek analiz değil" felsefesi), bu yüzden bilinen çakışan TAM
# kelimeler için küçük, elle bakımı yapılan bir istisna listesi tutuyoruz
# (27 Ağu 2026'da canlıda "gram altın" e-posta uyarısıyla bulundu — "İşgal
# altındaki topraklar" yanlışlıkla eşleşiyordu).
_FALSE_FRIEND_WORDS: Dict[str, FrozenSet[str]] = {
    "altın": frozenset({"altında", "altındaki", "altından", "altındayken"}),
}


def _term_occurs_in(term: str, text: str) -> bool:
    """`term` metinde bilinen bir yanlış-dost istisnası OLMADAN en az bir
    yerde geçiyor mu. `term`/`text` çağıran tarafta zaten `_tr_lower` ile
    küçültülmüş olmalı."""
    exclusions = _FALSE_FRIEND_WORDS.get(term)
    if not exclusions:
        return bool(re.search(r"\b" + re.escape(term), text))
    for m in re.finditer(r"\b" + re.escape(term) + r"\w*", text):
        if m.group(0) not in exclusions:
            return True
    return False


def _tr_lower(text: str) -> str:
    """Türkçe uyumlu küçük harfe çevirme. Python'un varsayılan `.lower()`'ı
    "İ" (U+0130) karakterini tek bir "i" değil "i" + birleşen nokta işaretine
    çevirir — bu da örn. kullanıcı "İSTANBUL" yazınca metindeki "istanbul"
    ile hiç eşleşmemesine yol açar. Önce İ/I'yı ASCII karşılıklarına
    sabitleyip öyle küçültmek bu sorunu ortadan kaldırır."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def matched_keyword(article: Article, keywords: List[str]) -> Optional[str]:
    """Başlık/özet/içerikte geçen ilk anahtar kelimeyi döner, yoksa None.

    Eşleşme kelimenin/ifadenin BAŞINDA aranır (`\\bifade`), metnin herhangi bir
    yerinde geçen ham bir alt dizi olarak DEĞİL — aksi halde "altın" gibi bir
    kök, "gözaltına" gibi dilbilgisel olarak alakasız bir kelimenin ORTASINDA
    da eşleşir (26 Ağu 2026'da canlıda bulunan bug, news_service._keyword_relevance
    ile aynı sınıf — bkz. o fonksiyonun docstring'i). Sağdan sınırlamıyoruz,
    çünkü çekim eklerini ("altının") yakalamak istiyoruz. Çok kelimeli bir
    keyword ("gram altın") için ifadenin YAN YANA geçmesi gerekir — boşluk da
    literal karakter olarak regex'e dahil olur.

    Bu \\b-anchor tek başına yetmiyor bazı köklerde: "altın" (gold) ile
    "altında"/"altındaki" ("alt" [under] kelimesinin çekimli hali) harf
    düzeyinde TAM AYNI — ikisinin de önünde gerçek bir kelime sınırı var,
    gerçek morfolojik analiz olmadan ayırt edilemez (27 Ağu 2026'da canlıda
    bulundu). `_term_occurs_in` bilinen böyle çakışmaları `_FALSE_FRIEND_WORDS`
    istisna listesiyle eler."""
    if not keywords:
        return None
    text = _tr_lower(f"{article.title} {article.summary or ''} {article.content[:500]}")
    for kw in keywords:
        if _term_occurs_in(_tr_lower(kw), text):
            return kw
    return None


def has_preferences(sub: Subscriber) -> bool:
    """Abone hiç tercih belirtmemiş mi (konu/kaynak/keyword) — belirtmemişse
    kişiselleştirme uygulanmaz, genel akış gönderilir."""
    return bool(sub.keywords or sub.preferred_topics or sub.preferred_sources)


def article_matches_subscriber(article: Article, sub: Subscriber) -> bool:
    """Haber, abonenin konu/kaynak/keyword tercihlerinden en az biriyle eşleşiyor mu (OR)."""
    if sub.preferred_topics and article.topic in sub.preferred_topics:
        return True
    if sub.preferred_sources and article.source in sub.preferred_sources:
        return True
    if matched_keyword(article, sub.keywords) is not None:
        return True
    return False
