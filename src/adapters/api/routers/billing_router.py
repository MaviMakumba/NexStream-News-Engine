"""Billing endpoint'leri (/billing) — Stripe abonelik akışı + dev-mode simülasyonu.

İki çalışma modu:
    1. Stripe modu (production): checkout → Stripe Checkout sayfası → webhook
       `customer.subscription.*` event'i → tier güncellemesi. Webhook imzası
       `STRIPE_WEBHOOK_SECRET` ile doğrulanır.
    2. Dev mode (BILLING_DEV_MODE=true): Stripe'a hiç gidilmez; checkout çağrısı
       tier'ı ANINDA günceller ve `dev_mode: true` döner. Lokal demo içindir,
       production'da asla açılmamalıdır.

Stripe yapılandırılmamış ve dev mode kapalıysa tüm endpoint'ler 503 döner.

v1.15: Her iki mod da `current_user.email_verified=True` ister — Free tier
erişimi etkilenmez, sadece ücretli kademeye yükseltme e-posta doğrulaması
şart koşar (bkz. auth_router.py::verify_email).
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.adapters.api.auth_utils import get_current_user
from src.adapters.api.limiter import limiter
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User
from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])

# Satın alınabilir kademeler — Free'ye "yükseltme" olmaz, o varsayılandır.
_PURCHASABLE_TIERS = ("pro", "enterprise")


class CheckoutRequest(BaseModel):
    tier: str  # "pro" | "enterprise"
    success_url: str
    cancel_url: str


def _require_stripe():
    """Stripe SDK'sını yapılandırıp döner; anahtar yoksa 503.

    Import fonksiyon içinde: Stripe kullanılmayan kurulumlarda (dev mode)
    modül yüklenmesin, app açılışı yavaşlamasın.
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    import stripe as _stripe
    _stripe.api_key = settings.stripe_secret_key
    return _stripe


# ── Yapılandırma keşfi ─────────────────────────────────────────────────────────

@router.get("/config")
def billing_config():
    """Frontend'in ödeme akışını seçmesi için public yapılandırma özeti.

    Sır içermez — sadece hangi modun aktif olduğunu söyler.
    """
    return {
        "dev_mode": bool(settings.billing_dev_mode),
        "stripe_configured": bool(settings.stripe_secret_key),
    }


# ── Checkout ───────────────────────────────────────────────────────────────────

@router.post("/checkout")
@limiter.limit("20/minute")
def create_checkout(
    request: Request,
    req: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Abonelik başlatır: Stripe Checkout URL'i veya dev modda anında yükseltme."""
    if req.tier not in _PURCHASABLE_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier. Use 'pro' or 'enterprise'")

    # v1.15: DNS/MX kontrolü (v1.14) sahte kullanıcı adı + gerçek domain kombinasyonunu
    # yakalayamıyordu — ücretli kademeye yükseltme artık e-posta doğrulaması ister.
    # Free tier'da erişim etkilenmez (bkz. auth_router.py::_send_verification_email).
    if not current_user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="E-posta adresinizi doğrulamadan plan yükseltemezsiniz. Hesap sayfanızdan doğrulama e-postasını yeniden gönderebilirsiniz.",
        )

    # Dev mode: ödeme simülasyonu — tier anında güncellenir, Stripe'a gidilmez.
    if settings.billing_dev_mode:
        UserRepository(db).update_tier(current_user.id, req.tier)
        logger.info("DEV MODE yükseltme: user_id=%s → %s", current_user.id, req.tier)
        return {"url": req.success_url, "dev_mode": True, "tier": req.tier}

    stripe = _require_stripe()
    price_map = {
        "pro": settings.stripe_pro_price_id,
        "enterprise": settings.stripe_enterprise_price_id,
    }
    price_id = price_map.get(req.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid tier. Use 'pro' or 'enterprise'")

    # Mevcut Stripe müşterisi varsa onu kullan; yoksa e-postadan yeni müşteri açılır.
    customer_kwargs = {}
    if current_user.stripe_customer_id:
        customer_kwargs["customer"] = current_user.stripe_customer_id
    else:
        customer_kwargs["customer_email"] = current_user.email

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            # metadata webhook'ta geri okunur — tier eşlemesi buradan yapılır
            metadata={"user_id": str(current_user.id), "tier": req.tier},
            **customer_kwargs,
        )
        return {"url": session.url}
    except Exception as e:
        logger.error("Stripe checkout hatası: %s", e)
        raise HTTPException(status_code=502, detail="Payment provider error")


@router.post("/dev/downgrade")
def dev_downgrade(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dev modda aboneliği iptal simülasyonu — tier'ı Free'ye çeker.

    Stripe modunda bu iş müşteri portalından yapılır; endpoint 404 döner.
    """
    if not settings.billing_dev_mode:
        raise HTTPException(status_code=404, detail="Not available")
    UserRepository(db).update_tier(current_user.id, "free")
    logger.info("DEV MODE düşürme: user_id=%s → free", current_user.id)
    return {"dev_mode": True, "tier": "free"}


# ── Stripe webhook ─────────────────────────────────────────────────────────────

@router.post("/webhook")
@limiter.limit("60/minute")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Stripe'tan gelen abonelik event'lerini işler (imza doğrulamalı)."""
    stripe = _require_stripe()
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event["type"]
    logger.info("Stripe webhook: %s", event_type)

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _handle_subscription_activated(event["data"]["object"])
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_cancelled(event["data"]["object"])

    return {"received": True}


def _handle_subscription_activated(subscription: dict) -> None:
    """Abonelik açıldı/güncellendi → kullanıcı tier'ını yükselt.

    Webhook request context'i dışında çalıştığı için kendi DB session'ını açar.
    """
    from src.infrastructure.config.database import SessionLocal
    customer_id = subscription.get("customer")
    metadata = subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    tier = metadata.get("tier", "pro")
    if not user_id:
        return
    db = SessionLocal()
    try:
        UserRepository(db).update_tier(int(user_id), tier, stripe_customer_id=customer_id)
        logger.info("Kullanıcı tier güncellendi: user_id=%s, tier=%s", user_id, tier)
    finally:
        db.close()


def _handle_subscription_cancelled(subscription: dict) -> None:
    """Abonelik iptal → kullanıcı Free kademesine döner."""
    from src.infrastructure.config.database import SessionLocal
    metadata = subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    if not user_id:
        return
    db = SessionLocal()
    try:
        UserRepository(db).update_tier(int(user_id), "free")
        logger.info("Abonelik iptal: user_id=%s → free tier", user_id)
    finally:
        db.close()


# ── Müşteri portalı ────────────────────────────────────────────────────────────

@router.get("/portal")
def billing_portal(current_user: User = Depends(get_current_user)):
    """Stripe müşteri portalı URL'i — fatura görüntüleme/iptal buradan yapılır."""
    stripe = _require_stripe()
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No active subscription found. Please subscribe first.")
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
        )
        return {"url": session.url}
    except Exception as e:
        logger.error("Stripe portal hatası: %s", e)
        raise HTTPException(status_code=502, detail="Payment provider error")
