"""Kaynak güvenilirlik skorlaması.

İki bileşen:
1. base_credibility — kaynağa elle atanmış taban güven puanı (config seed).
2. corroboration — aynı olayı (entity örtüşmesi) kaç FARKLI kaynağın da raporladığı.
   Çapraz doğrulama arttıkça güven artar.
"""

# Kaynak taban güven puanları (0-1). Elle seed; yeni kaynak eklenince buraya bir satır.
SOURCE_CREDIBILITY: dict = {
    # İngilizce
    "BBC Technology": 0.90,
    "BBC Sport":      0.85,
    "Guardian Tech":  0.85,
    "TechCrunch":     0.75,
    "The Verge":      0.75,
    "Hacker News":    0.60,
    # Türkçe
    "BBC Türkçe":     0.90,
    "Anadolu Ajansı": 0.75,
    "AA Ekonomi":     0.75,
    "TRT Haber":      0.70,
    "CNN Türk":       0.70,
    "Hürriyet":       0.65,
    "Hürriyet Spor":  0.65,
    "Habertürk":      0.65,
    "HT Spor":        0.65,
    "Sabah":          0.60,
    "Sözcü":          0.60,
}

DEFAULT_CREDIBILITY = 0.50
_CORROBORATION_STEP = 0.05   # her ek doğrulayan kaynak başına artış
_CORROBORATION_CAP = 0.20    # corroboration kaynaklı maksimum artış


def base_credibility(source: str) -> float:
    return SOURCE_CREDIBILITY.get(source, DEFAULT_CREDIBILITY)


def compute_credibility(base: float, corroboration_count: int) -> float:
    boost = min(max(corroboration_count, 0) * _CORROBORATION_STEP, _CORROBORATION_CAP)
    return round(min(base + boost, 1.0), 4)
