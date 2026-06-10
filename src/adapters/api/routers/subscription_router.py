"""Newsletter abonelik endpoint'leri (/subscriptions).

Kayıt ve iptal publictir (kullanıcı kendisi yönetir); tercih okuma/güncelleme
X-API-Key gerektirir (başkasının aboneliğini kurcalamayı engeller).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from src.infrastructure.config.database import SessionLocal
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.notifications.email_adapter import get_email_adapter
from src.domain.models.subscriber import Subscriber
from src.adapters.api.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


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


@router.post("/", status_code=status.HTTP_201_CREATED)
def subscribe(req: SubscribeRequest, repo: SubscriberRepository = Depends(_get_repo)):
    if req.frequency not in ("daily", "instant", "never"):
        raise HTTPException(status_code=400, detail="frequency must be daily, instant or never")

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


@router.delete("/{email}", status_code=status.HTTP_200_OK)
def unsubscribe(email: str, repo: SubscriberRepository = Depends(_get_repo)):
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
