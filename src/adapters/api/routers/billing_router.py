import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.adapters.api.auth_utils import get_current_user
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User
from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    tier: str  # "pro" | "enterprise"
    success_url: str
    cancel_url: str


def _require_stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    import stripe as _stripe
    _stripe.api_key = settings.stripe_secret_key
    return _stripe


@router.post("/checkout")
def create_checkout(
    req: CheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    stripe = _require_stripe()
    price_map = {
        "pro": settings.stripe_pro_price_id,
        "enterprise": settings.stripe_enterprise_price_id,
    }
    price_id = price_map.get(req.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid tier. Use 'pro' or 'enterprise'")

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
            metadata={"user_id": str(current_user.id), "tier": req.tier},
            **customer_kwargs,
        )
        return {"url": session.url}
    except Exception as e:
        logger.error("Stripe checkout hatası: %s", e)
        raise HTTPException(status_code=502, detail="Payment provider error")


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
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
    from src.infrastructure.config.database import SessionLocal
    customer_id = subscription.get("customer")
    metadata = subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    tier = metadata.get("tier", "pro")
    if not user_id:
        return
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        repo.update_tier(int(user_id), tier, stripe_customer_id=customer_id)
        logger.info("Kullanıcı tier güncellendi: user_id=%s, tier=%s", user_id, tier)
    finally:
        db.close()


def _handle_subscription_cancelled(subscription: dict) -> None:
    from src.infrastructure.config.database import SessionLocal
    metadata = subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    if not user_id:
        return
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        repo.update_tier(int(user_id), "free")
        logger.info("Abonelik iptal: user_id=%s → free tier", user_id)
    finally:
        db.close()


@router.get("/portal")
def billing_portal(current_user: User = Depends(get_current_user)):
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
