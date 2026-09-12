"""Güvenlik günlüğüne olay yazan tek yardımcı (13 Eylül 2026).

Router'lar bir satırla çağırır; IP / user-agent / request_id / path istekten
otomatik alınır. Fail-open: yazılamazsa (tablo henüz yok, DB hatası) istek
bozulmaz, sadece loglanır — projenin "exception yut, logla, fallback" ilkesi.
İmza gizli bilgi (parola, token, anahtar) taşımaya izin vermez: sadece
e-posta, kullanıcı id'si ve kısa bir `detail` metni.
"""

import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from src.adapters.api.request_context import client_ip, current_request_id
from src.adapters.repositories.security_event_repository import SecurityEventRepository
from src.domain.models.security_event import SecurityEvent

logger = logging.getLogger(__name__)


def record_security_event(
    db: Session,
    request: Request,
    category: str,
    event_type: str,
    *,
    email: Optional[str] = None,
    user_id: Optional[int] = None,
    detail: Optional[str] = None,
) -> None:
    try:
        SecurityEventRepository(db).record(SecurityEvent(
            category=category,
            event_type=event_type,
            email=email.strip().lower() if email else None,
            user_id=user_id,
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_id=current_request_id(),
            path=request.url.path,
            detail=detail,
        ))
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("Güvenlik günlüğü yazılamadı (%s/%s): %s", category, event_type, e)
