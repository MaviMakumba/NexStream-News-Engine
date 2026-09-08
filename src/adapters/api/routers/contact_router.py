"""İletişim / telif itirazı formu (/contact) — public, kimlik doğrulama gerektirmez.

Roadmap madde 9 (CLAUDE.md): "/privacy"+"/terms"te "bizimle iletişime geçin"
deniyordu ama gerçek bir kanal yoktu. Buradaki tasarım bilinçli olarak
kişisel e-postayı public'e sergilemiyor — mesaj Resend/SMTP üzerinden
`CONTACT_RECIPIENT_EMAIL`'e iletiliyor, gönderenin adresi Reply-To header'ı
olarak taşınıyor (sahibi doğrudan "yanıtla"ya basabilir).
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from src.adapters.notifications.email_adapter import get_email_adapter
from src.adapters.api.limiter import limiter
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contact", tags=["Contact"])


class ContactRequest(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    category: Literal["general", "takedown"] = "general"
    message: str = Field(..., min_length=1, max_length=5000)
    language: str = "TR"


@router.post("/")
@limiter.limit("5/minute")
def submit_contact(request: Request, req: ContactRequest):
    """Mesajı `CONTACT_RECIPIENT_EMAIL`'e iletir.

    Yapılandırılmamışsa 503 (billing_router'ın "yapılandırılmazsa 503"
    deseniyle aynı) — sessizce console'a düşüp mesajın kaybolması yerine.
    Sağlayıcı gönderimi başarısız olursa 502 (billing_router'daki "Payment
    provider error" ile aynı desen) — forgot-password'ün aksine burada bir
    user-enumeration riski yok, göndereni sessizce oyalamanın faydası yok.
    """
    if not settings.contact_recipient_email:
        raise HTTPException(status_code=503, detail="Contact channel not configured")

    ok = get_email_adapter().send_contact_message(
        to=settings.contact_recipient_email,
        name=req.name or "",
        from_email=req.email,
        category=req.category,
        message=req.message,
        language=req.language,
    )
    if not ok:
        logger.error("İletişim mesajı gönderilemedi: from=%s category=%s", req.email, req.category)
        raise HTTPException(status_code=502, detail="Message could not be delivered")

    logger.info("İletişim mesajı gönderildi: from=%s category=%s", req.email, req.category)
    return {"success": True}
