"""Bir haberin bir abonenin tercihleriyle eşleşip eşleşmediğini belirleyen saf
domain mantığı — dış bağımlılık yok (bkz. domain/scoring/ ile aynı felsefe).

Hem anlık keyword alert'te (news_service.py) hem günlük digest
kişiselleştirmesinde (newsletter_job.py) kullanılır — eskiden ikisi de kendi
keyword eşleştirme mantığını ayrı ayrı yazıyordu.
"""

import re
from typing import List, Optional
from src.domain.models.article import Article
from src.domain.models.subscriber import Subscriber


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
    literal karakter olarak regex'e dahil olur."""
    if not keywords:
        return None
    text = _tr_lower(f"{article.title} {article.summary or ''} {article.content[:500]}")
    for kw in keywords:
        if re.search(r"\b" + re.escape(_tr_lower(kw)), text):
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
