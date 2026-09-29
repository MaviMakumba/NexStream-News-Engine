"""Haber konuları için TEK doğruluk kaynağı (29 Eylül 2026, S1).

Eskiden aynı liste 5+ yerde elle kopyalanıyordu (analiz prompt'u, e-posta
etiketleri, frontend filtre/bülten/etiket sözlükleri). Buraya yeni bir konu
eklemek = `TOPICS`'a bir `Topic` satırı + `python scripts/gen_frontend_topics.py`.

Kimlikler (`Topic.id`) İngilizce sabit değerlerdir ve DB'de bu haliyle saklanır —
ASLA yeniden adlandırma. Etiketler dil sözlüğüdür (yeni dil = anahtar eklemek).
`hint`: yalnızca birbirine karışan konular için analiz prompt'una giren kısa ipucu
(her karakter her Groq çağrısında tekrarlanır → kısa tut).
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, FrozenSet, Mapping, Tuple


@dataclass(frozen=True)
class Topic:
    """Değiştirilemez kayıt: `labels` salt-okunur görünüme sarılır (tek doğruluk kaynağı kodun
    başka bir yerinden sessizce bozulamaz) ve hash'e katılmaz (Mapping hash'lenemez)."""
    id: str
    labels: Mapping[str, str] = field(default_factory=dict, hash=False)
    hint: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


TOPICS: Tuple[Topic, ...] = (
    Topic("Technology", {"TR": "Teknoloji", "EN": "Technology"}),
    Topic("Sports", {"TR": "Spor", "EN": "Sports"}),
    Topic("Economy", {"TR": "Ekonomi", "EN": "Economy"}, "markets, business, not crypto"),
    Topic("Politics", {"TR": "Siyaset", "EN": "Politics"}),
    Topic("Health", {"TR": "Sağlık", "EN": "Health"}),
    Topic("Culture", {"TR": "Kültür", "EN": "Culture"}, "arts, literature, history"),
    Topic("World", {"TR": "Dünya", "EN": "World"}),
    Topic("Science", {"TR": "Bilim", "EN": "Science"}, "research, space"),
    Topic("Crypto", {"TR": "Kripto", "EN": "Crypto"}, "cryptocurrency, blockchain"),
    Topic("Environment", {"TR": "Çevre & İklim", "EN": "Environment & Climate"}, "climate, nature"),
    Topic("Entertainment", {"TR": "Eğlence", "EN": "Entertainment"}, "celebrities, film, music, TV"),
    Topic("Other", {"TR": "Diğer", "EN": "Other"}),
)

VALID_TOPIC_IDS: FrozenSet[str] = frozenset(t.id for t in TOPICS)
_BY_ID: Dict[str, Topic] = {t.id: t for t in TOPICS}


def topic_label(topic_id: str, language: str, fallback_language: str = "EN") -> str:
    """Konu etiketi. Bilinmeyen dil → `fallback_language`; kayıt defterinde olmayan
    kimlik → kimliğin kendisi (UI/e-posta asla boş kalmaz)."""
    if not topic_id:
        return ""
    topic = _BY_ID.get(topic_id)
    if topic is None:
        return topic_id
    return topic.labels.get(language) or topic.labels.get(fallback_language) or topic_id


def normalize_topic(value: object) -> str:
    """Model çıktısını geçerli bir konu kimliğine indirger; geçersiz her şey → 'Other'."""
    return value if isinstance(value, str) and value in VALID_TOPIC_IDS else "Other"
