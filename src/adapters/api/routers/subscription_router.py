"""Newsletter abonelik endpoint'leri (/subscriptions).

Kayıt ve iptal publictir (kullanıcı kendisi yönetir); tercih okuma/güncelleme
X-API-Key gerektirir (başkasının aboneliğini kurcalamayı engeller).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from src.infrastructure.config.database import SessionLocal
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.repositories.user_repository import UserRepository
from src.adapters.notifications.email_adapter import get_email_adapter
from src.domain.models.subscriber import Subscriber
from src.domain.models.user import UserTier, tier_at_least
from src.adapters.api.auth import verify_api_key
from src.adapters.api.auth_utils import user_effective_tier
from src.adapters.api.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

_UNSUBSCRIBE_CONFIRM_HTML = {
    "TR": ("Aboneliğiniz iptal edildi", "Artık NexStream'den e-posta almayacaksınız."),
    "EN": ("You've been unsubscribed", "You will no longer receive emails from NexStream."),
}
_UNSUBSCRIBE_NOTFOUND_HTML = {
    "TR": ("Abone bulunamadı", "Bu e-posta adresi için aktif bir abonelik bulunamadı."),
    "EN": ("Subscriber not found", "No active subscription was found for this email address."),
}


def _confirmation_page(title: str, body: str) -> str:
    return f"""<html><body style='font-family:sans-serif;max-width:480px;margin:80px auto;text-align:center'>
<h2 style='color:#1a1a1a'>{title}</h2>
<p style='color:#666'>{body}</p>
</body></html>"""


class SubscribeRequest(BaseModel):
    email: EmailStr
    keywords: List[str] = []
    preferred_sources: List[str] = []
    preferred_topics: List[str] = []
    language: str = "TR"
    frequency: str = "daily"


class PreferencesUpdateRequest(BaseModel):
    keywords: Optional[List[str]] = None
    preferred_sources: Optional[List[str]] = None
    preferred_topics: Optional[List[str]] = None
    language: Optional[str] = None
    frequency: Optional[str] = None


def _get_repo() -> SubscriberRepository:
    db = SessionLocal()
    try:
        yield SubscriberRepository(db)
    finally:
        db.close()


def _get_user_repo() -> UserRepository:
    db = SessionLocal()
    try:
        yield UserRepository(db)
    finally:
        db.close()


def _assert_instant_allowed(email: str, frequency: str, users: UserRepository) -> None:
    """Anlık (instant) keyword alert Pro+ özelliğidir.

    Subscriber e-posta bazlı ve User hesabından bağımsız tasarlandığı için
    (bkz. CLAUDE.md) yetki kontrolü aynı e-postayla kayıtlı bir User'ın
    tier'ına bakarak yapılır — kayıtsız/Free e-postalar instant isteyemez.
    """
    if frequency != "instant":
        return
    user = users.get_by_email(email)
    if not user or not tier_at_least(user_effective_tier(user), UserTier.PRO):
        raise HTTPException(
            status_code=403,
            detail="Anlık uyarılar Pro plan gerektirir — bu e-postayla kayıtlı bir Pro/Kurumsal hesap gerekli. "
                   "/ Instant alerts require a Pro plan registered with this email.",
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def subscribe(
    request: Request,
    req: SubscribeRequest,
    repo: SubscriberRepository = Depends(_get_repo),
    users: UserRepository = Depends(_get_user_repo),
):
    if req.frequency not in ("daily", "instant", "never"):
        raise HTTPException(status_code=400, detail="frequency must be daily, instant or never")
    _assert_instant_allowed(req.email, req.frequency, users)

    sub = Subscriber(
        email=req.email,
        keywords=[k.strip() for k in req.keywords if k.strip()],
        preferred_sources=req.preferred_sources,
        preferred_topics=req.preferred_topics,
        language=req.language,
        frequency=req.frequency,
    )
    saved = repo.save_subscriber(sub)
    try:
        get_email_adapter().send_welcome(req.email, req.language)
    except Exception as e:
        logger.warning("Welcome email gönderilemedi: %s", e)
    logger.info("Yeni abone: %s", req.email)
    return {"email": saved.email, "frequency": saved.frequency, "active": saved.is_active}


@router.get("/unsubscribe", response_class=HTMLResponse)
@limiter.limit("20/minute")
def unsubscribe_via_link(request: Request, email: str, lang: str = "TR", repo: SubscriberRepository = Depends(_get_repo)):
    """E-postadaki tıklanabilir 'aboneliği iptal et' linkinin hedefi — tarayıcıda
    açılan basit bir onay sayfası döner (JSON değil, çünkü doğrudan e-posta
    istemcisinden/tarayıcıdan tıklanır). Bu route `/{email}` parametreli
    route'lardan ÖNCE tanımlanmalı, yoksa "unsubscribe" bir e-posta adresi
    sanılıp oraya yönlenir."""
    ok = repo.deactivate(email)
    title, body = (_UNSUBSCRIBE_CONFIRM_HTML if ok else _UNSUBSCRIBE_NOTFOUND_HTML).get(
        lang, _UNSUBSCRIBE_CONFIRM_HTML["TR"] if ok else _UNSUBSCRIBE_NOTFOUND_HTML["TR"]
    )
    if ok:
        logger.info("Abonelik iptal edildi (link): %s", email)
    return _confirmation_page(title, body)


@router.delete("/{email}", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
def unsubscribe(request: Request, email: str, repo: SubscriberRepository = Depends(_get_repo)):
    ok = repo.deactivate(email)
    if not ok:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    logger.info("Abonelik iptal edildi: %s", email)
    return {"message": "Unsubscribed successfully", "email": email}


@router.patch("/{email}", dependencies=[Depends(verify_api_key)])
def update_preferences(
    email: str,
    req: PreferencesUpdateRequest,
    repo: SubscriberRepository = Depends(_get_repo),
    users: UserRepository = Depends(_get_user_repo),
):
    sub = repo.get_by_email(email)
    if not sub or not sub.is_active:
        raise HTTPException(status_code=404, detail="Active subscriber not found")

    if req.keywords is not None:
        sub.keywords = [k.strip() for k in req.keywords if k.strip()]
    if req.preferred_sources is not None:
        sub.preferred_sources = req.preferred_sources
    if req.preferred_topics is not None:
        sub.preferred_topics = req.preferred_topics
    if req.language is not None:
        sub.language = req.language
    if req.frequency is not None:
        if req.frequency not in ("daily", "instant", "never"):
            raise HTTPException(status_code=400, detail="frequency must be daily, instant or never")
        _assert_instant_allowed(email, req.frequency, users)
        sub.frequency = req.frequency

    repo.update_subscriber(sub)
    return {"email": sub.email, "updated": True}


@router.get("/{email}", dependencies=[Depends(verify_api_key)])
def get_subscription(email: str, repo: SubscriberRepository = Depends(_get_repo)):
    sub = repo.get_by_email(email)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {
        "email": sub.email,
        "keywords": sub.keywords,
        "preferred_sources": sub.preferred_sources,
        "preferred_topics": sub.preferred_topics,
        "language": sub.language,
        "frequency": sub.frequency,
        "is_active": sub.is_active,
    }
