"""Kaynak başına günlük tavan çözümleme (29 Eylül 2026, S2).

Varsayılan tavan scraper sınıfında (`daily_cap`) yaşar; operasyonel ayar için ortam
değişkeni `SOURCE_DAILY_CAPS` (JSON: {"CNN Türk": 80}) bunu geçersiz kılar — kod
değişmeden, Grafana'daki `nexstream_source_capped_total`'a bakarak ayarlanır.
Bozuk ayar uygulamayı ASLA düşürmez: uyarı loglanır, varsayılanlara dönülür.
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def parse_cap_overrides(raw: str) -> Dict[str, int]:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        logger.warning("SOURCE_DAILY_CAPS geçerli JSON değil, yok sayılıyor: %r", raw[:80])
        return {}
    if not isinstance(data, dict):
        logger.warning("SOURCE_DAILY_CAPS bir JSON nesnesi olmalı, yok sayılıyor")
        return {}

    overrides: Dict[str, int] = {}
    for source, value in data.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            logger.warning("SOURCE_DAILY_CAPS[%s]=%r geçersiz (pozitif sayı olmalı), atlandı", source, value)
            continue
        overrides[source] = int(value)
    return overrides


def effective_daily_cap(source_name: str, default: Optional[int], overrides: Dict[str, int]) -> Optional[int]:
    """Override > sınıf varsayılanı > None (sınırsız)."""
    return overrides.get(source_name, default)
