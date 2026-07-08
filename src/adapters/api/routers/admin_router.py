"""Admin endpoint'leri (/admin) — kullanım istatistikleri, kullanıcı/rol yönetimi + sponsor CRUD.

Yetkilendirme (v1.13, iki seviyeli):
    require_moderator — router genelinde: GÖRÜNTÜLEME (kullanım/kullanıcı/sponsor
        listeleri). X-API-Key VEYA moderator/admin rolündeki kullanıcı oturumu.
    require_admin — YAZMA işlemleri (rol değiştirme, sponsor CRUD) route
        düzeyinde ayrıca ister. X-API-Key VEYA role="admin" (veya ADMIN_EMAILS'teki).

Sponsor yönetimi kasıtlı olarak basit tutuldu (tek tablo, soft-delete):
silme yerine `is_active=false` yazılır ki geçmiş kampanyalar raporlanabilsin.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.adapters.api.auth_utils import require_admin, require_moderator, get_current_user, effective_role
from src.adapters.repositories.user_repository import UserRepository
from src.adapters.repositories.orm_models import SponsorORM
from src.domain.models.sponsor import Sponsor
from src.domain.models.user import User, UserRole
from src.infrastructure.config.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_moderator)])


# ── Kullanım istatistikleri ────────────────────────────────────────────────────

@router.get("/usage")
def get_usage_stats(
    user_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Endpoint bazında istek sayısı/ortalama gecikme — opsiyonel kullanıcı filtresi."""
    repo = UserRepository(db)
    return repo.get_usage_stats(user_id=user_id, days=days)


# ── Müşteri/kullanıcı listesi ───────────────────────────────────────────────────

@router.get("/users")
def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tier: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Kayıtlı tüm kullanıcılar — tier, aktiflik ve gerçek ödeme durumu.

    `is_paying`, `stripe_customer_id`'nin dolu olup olmadığından türetilir:
    BILLING_DEV_MODE'daki tek-tık tier yükseltmeleri bu alanı hiç YAZMAZ
    (bkz. billing_router.py), sadece gerçek Stripe checkout/webhook yazar —
    yani bu alan "dev-mode'da yükseltilmiş" ile "gerçekten ödeyen" ayrımını verir.
    """
    repo = UserRepository(db)
    users = repo.list_users(limit=limit, offset=offset, tier=tier)
    return {
        "total": repo.count_users(tier=tier),
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "tier": u.tier.value if hasattr(u.tier, "value") else u.tier,
                "is_active": u.is_active,
                "role": effective_role(u),
                "is_paying": bool(u.stripe_customer_id),
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


class RoleUpdateRequest(BaseModel):
    role: str


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_admin)])
def update_user_role(
    user_id: int,
    req: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Başka bir kullanıcının rolünü değiştirir — sadece admin.

    Kendi rolünüzü admin'den düşüremezsiniz (yanlışlıkla kilitlenmeyi önler).
    """
    if req.role not in (UserRole.USER.value, UserRole.MODERATOR.value, UserRole.ADMIN.value):
        raise HTTPException(status_code=400, detail="role must be user, moderator or admin")
    if user_id == current_user.id and req.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=400, detail="Kendi admin rolünüzü kendiniz düşüremezsiniz.")
    repo = UserRepository(db)
    if not repo.update_role(user_id, req.role):
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("Rol değişti: user_id=%s → %s (işlemi yapan: %s)", user_id, req.role, current_user.email)
    return {"id": user_id, "role": req.role}


# ── Sponsor CRUD ───────────────────────────────────────────────────────────────

class SponsorRequest(BaseModel):
    name: str
    url: str
    message: str
    active_from: datetime
    active_until: datetime


def _to_dict(orm: SponsorORM) -> dict:
    return {
        "id": orm.id,
        "name": orm.name,
        "url": orm.url,
        "message": orm.message,
        "active_from": orm.active_from,
        "active_until": orm.active_until,
        "is_active": orm.is_active,
    }


@router.get("/sponsors")
def list_sponsors(db: Session = Depends(get_db)):
    rows = db.query(SponsorORM).order_by(text("active_from DESC")).all()
    return [_to_dict(r) for r in rows]


@router.post("/sponsors", status_code=201, dependencies=[Depends(require_admin)])
def create_sponsor(req: SponsorRequest, db: Session = Depends(get_db)):
    orm = SponsorORM(
        name=req.name,
        url=req.url,
        message=req.message,
        active_from=req.active_from,
        active_until=req.active_until,
        is_active=True,
    )
    db.add(orm)
    db.commit()
    db.refresh(orm)
    logger.info("Yeni sponsor: %s", req.name)
    # Yanıt req'ten kurulur: testlerdeki mock session'larda ORM lazy-load tetiklenmesin
    return {
        "id": getattr(orm, "id", None),
        "name": req.name,
        "url": req.url,
        "message": req.message,
        "active_from": req.active_from,
        "active_until": req.active_until,
        "is_active": True,
    }


@router.patch("/sponsors/{sponsor_id}", dependencies=[Depends(require_admin)])
def update_sponsor(sponsor_id: int, req: SponsorRequest, db: Session = Depends(get_db)):
    orm = db.get(SponsorORM, sponsor_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    orm.name = req.name
    orm.url = req.url
    orm.message = req.message
    orm.active_from = req.active_from
    orm.active_until = req.active_until
    db.commit()
    return _to_dict(orm)


@router.delete("/sponsors/{sponsor_id}", dependencies=[Depends(require_admin)])
def deactivate_sponsor(sponsor_id: int, db: Session = Depends(get_db)):
    """Soft-delete: kayıt silinmez, sadece pasife alınır."""
    orm = db.get(SponsorORM, sponsor_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    orm.is_active = False
    db.commit()
    return {"id": sponsor_id, "is_active": False}


def get_active_sponsor(db: Session) -> Optional[Sponsor]:
    """Şu an yayında olan sponsoru döner (newsletter footer'ında kullanılır)."""
    now = datetime.now(timezone.utc)
    orm = (
        db.query(SponsorORM)
        .filter(
            SponsorORM.is_active.is_(True),
            SponsorORM.active_from <= now,
            SponsorORM.active_until >= now,
        )
        .first()
    )
    if not orm:
        return None
    return Sponsor(
        id=orm.id,
        name=orm.name,
        url=orm.url,
        message=orm.message,
        active_from=orm.active_from,
        active_until=orm.active_until,
        is_active=orm.is_active,
    )
